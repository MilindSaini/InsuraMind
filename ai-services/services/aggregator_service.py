"""Document-level aggregator — runs ONCE after all sections are processed.

Fully DTR-driven: reads section_taxonomy to know which card categories to
produce. For insurance_policy it builds coverage/exclusion/waiting_period cards;
for loan_agreement it builds terms/repayment/default/security cards; etc.

Any new doc type added to DTR automatically gets its own card categories.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Optional

from config import get_settings
from models.schemas import AggregatorResult
from utils.logging import get_logger

if TYPE_CHECKING:
    from dtr.models import DTRConfig

log = get_logger("services.aggregator")


class AggregatorService:
    """Produces a document-level summary, section cards, and risk summary."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None

    def _get_client(self):
        if self._client is None:
            if self.settings.gemini_api_key:
                try:
                    from google import genai
                    self._client = genai.Client(api_key=self.settings.gemini_api_key)
                except Exception as exc:
                    log.warning("aggregator.gemini_init_failed", error=str(exc))
        return self._client

    async def aggregate(
        self,
        clauses: list[dict],
        entities: list[dict],
        dtr_config: Optional["DTRConfig"] = None,
    ) -> AggregatorResult:
        """Build document-level aggregation from all processed sections.

        Args:
            clauses: All StructuredClause dicts from every section.
            entities: All extracted entity dicts.
            dtr_config: The DTR config for this document type.

        Returns:
            AggregatorResult with dynamic section_cards keyed by taxonomy.
        """
        # ── 1. Build section cards (DTR-driven) ──────────────────────────────
        section_cards = self._build_section_cards(clauses, dtr_config)

        # ── 2. Build entity summary ──────────────────────────────────────────
        entity_summary = self._build_entity_summary(entities, dtr_config)

        # ── 3. Build risk summary ────────────────────────────────────────────
        risk_summary = self._build_risk_summary(clauses, dtr_config)

        # ── 4. Generate document summary (single LLM call) ──────────────────
        document_summary = await self._generate_document_summary(
            clauses, section_cards, entity_summary, dtr_config
        )

        result = AggregatorResult(
            document_summary=document_summary,
            section_cards=section_cards,
            risk_summary=risk_summary,
            entity_summary=entity_summary,
        )

        log.info(
            "aggregator.complete",
            doc_type=dtr_config.doc_type if dtr_config else "unknown",
            card_categories=len(section_cards),
            total_cards=sum(len(v) for v in section_cards.values()),
            entity_count=len(entity_summary),
            risk_level=risk_summary.get("overall_risk_level", "unknown"),
        )

        return result

    # ── Section cards (DTR-driven) ────────────────────────────────────────────

    def _build_section_cards(
        self,
        clauses: list[dict],
        dtr_config: Optional["DTRConfig"],
    ) -> dict[str, list[dict]]:
        """Group clauses by section taxonomy and build summary cards.

        The keys are determined by dtr_config.section_taxonomy.
        For insurance_policy: {"coverage": [...], "exclusion": [...], ...}
        For loan_agreement:   {"terms": [...], "repayment": [...], ...}
        """
        # Determine card categories from DTR
        if dtr_config and dtr_config.section_taxonomy:
            categories = set(dtr_config.section_taxonomy.keys())
        else:
            # Fallback: derive categories from the clauses themselves
            categories = {c.get("clause_type", "general") for c in clauses}

        # Group clauses by their clause_type
        grouped: dict[str, list[dict]] = {cat: [] for cat in categories}
        uncategorized: list[dict] = []

        for clause in clauses:
            clause_type = clause.get("clause_type", "general")
            if clause_type in grouped:
                grouped[clause_type].append(clause)
            else:
                uncategorized.append(clause)

        # Build card objects for each category
        section_cards: dict[str, list[dict]] = {}

        for category, category_clauses in grouped.items():
            if not category_clauses:
                continue
            cards = []
            for c in category_clauses:
                card = {
                    "title": c.get("title", ""),
                    "value": c.get("full_text", c.get("value", "")),
                    "confidence": c.get("confidence", 0.0),
                    "risk_level": c.get("risk_level", "low"),
                    "risk_score": c.get("risk_score", 0.0),
                    "extraction_method": c.get("extraction_method", "unknown"),
                    "page_number": c.get("source_section", {}).get("page_number"),
                }
                cards.append(card)
            section_cards[category] = cards

        # Add uncategorized clauses under "general" if any
        if uncategorized:
            general_cards = section_cards.get("general", [])
            for c in uncategorized:
                general_cards.append({
                    "title": c.get("title", ""),
                    "value": c.get("value", ""),
                    "confidence": c.get("confidence", 0.0),
                    "risk_level": c.get("risk_level", "low"),
                    "extraction_method": c.get("extraction_method", "unknown"),
                })
            section_cards["general"] = general_cards

        return section_cards

    # ── Entity summary ────────────────────────────────────────────────────────

    def _build_entity_summary(
        self,
        entities: list[dict],
        dtr_config: Optional["DTRConfig"],
    ) -> dict[str, str]:
        """Map entity_schema keys to their best-extracted values.

        For insurance_policy: {"policy_number": "ABC123", "sum_insured": "5,00,000", ...}
        For loan_agreement:   {"principal": "10,00,000", "interest_rate": "9.5%", ...}
        """
        if not entities:
            return {}

        # Group entities by type, pick highest-confidence value per type
        best: dict[str, tuple[float, str]] = {}
        for entity in entities:
            etype = entity.get("entityType") or entity.get("entity_type", "")
            evalue = entity.get("entityValue") or entity.get("entity_value", "")
            confidence = entity.get("confidence", 0.0)

            if etype and evalue:
                current = best.get(etype)
                if current is None or confidence > current[0]:
                    best[etype] = (confidence, evalue)

        return {k: v[1] for k, v in best.items()}

    # ── Risk summary ──────────────────────────────────────────────────────────

    def _build_risk_summary(
        self,
        clauses: list[dict],
        dtr_config: Optional["DTRConfig"],
    ) -> dict:
        """Aggregate risk across all clauses."""
        if not clauses:
            return {"overall_risk_level": "low", "overall_risk_score": 0.0, "risk_items": []}

        risk_scores = [c.get("risk_score", 0.0) for c in clauses]
        high_risk_clauses = [c for c in clauses if c.get("risk_level") == "high"]
        medium_risk_clauses = [c for c in clauses if c.get("risk_level") == "medium"]

        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0
        max_risk = max(risk_scores) if risk_scores else 0.0

        # Overall risk level
        if len(high_risk_clauses) >= 2 or max_risk >= 8.0:
            overall_level = "high"
        elif high_risk_clauses or len(medium_risk_clauses) >= 3 or avg_risk >= 4.0:
            overall_level = "medium"
        else:
            overall_level = "low"

        # Build risk items (top risks)
        risk_items = []
        for c in sorted(clauses, key=lambda x: x.get("risk_score", 0.0), reverse=True)[:5]:
            if c.get("risk_score", 0.0) > 0:
                risk_items.append({
                    "title": c.get("title", ""),
                    "risk_level": c.get("risk_level", "low"),
                    "risk_score": c.get("risk_score", 0.0),
                    "risk_reason": c.get("risk_reason", ""),
                    "section_type": c.get("clause_type", "general"),
                })

        # Flag DTR risk patterns found
        flagged_patterns = []
        if dtr_config and dtr_config.risk_patterns:
            all_text = " ".join(c.get("value", "") for c in clauses).lower()
            for pattern in dtr_config.risk_patterns:
                readable = pattern.replace("_", " ")
                if any(word in all_text for word in readable.split()):
                    flagged_patterns.append(readable)

        return {
            "overall_risk_level": overall_level,
            "overall_risk_score": round(avg_risk, 2),
            "max_risk_score": round(max_risk, 2),
            "high_risk_count": len(high_risk_clauses),
            "medium_risk_count": len(medium_risk_clauses),
            "risk_items": risk_items,
            "flagged_patterns": flagged_patterns,
        }

    # ── Document summary (single LLM call) ───────────────────────────────────

    async def _generate_document_summary(
        self,
        clauses: list[dict],
        section_cards: dict[str, list[dict]],
        entity_summary: dict[str, str],
        dtr_config: Optional["DTRConfig"],
    ) -> str:
        """Generate a concise document summary using Gemini Flash.

        This is the only LLM call in the aggregator — one call for the
        entire document, not per-section.
        """
        client = self._get_client()
        if client is None:
            return self._fallback_summary(section_cards, entity_summary, dtr_config)

        doc_type_name = dtr_config.display_name if dtr_config else "document"
        regulatory = dtr_config.regulatory_context if dtr_config else ""

        # Build a concise representation for the LLM
        cards_text = ""
        for section_key, cards in section_cards.items():
            cards_text += f"\n## {section_key.replace('_', ' ').title()}\n"
            for card in cards[:5]:  # Limit to avoid token overflow
                cards_text += f"- {card.get('title', '')}: {card.get('value', '')[:400]}\n"

        entities_text = "\n".join(f"- {k}: {v}" for k, v in entity_summary.items())

        prompt = f"""You are a professional document analyst. Summarize this {doc_type_name} in 3-5 sentences.

Key Entities:
{entities_text}

Section Breakdown:
{cards_text}

{"Regulatory context: " + regulatory if regulatory else ""}

Write a clear, professional summary highlighting the most important aspects.
Focus on key terms, amounts, conditions, and any notable risks.
"""
        try:
            from google.genai import types

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.settings.gemini_fast_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=1024,
                ),
            )
            return (getattr(response, "text", None) or "").strip()
        except Exception as exc:
            log.warning("aggregator.summary_failed", error=str(exc))
            return self._fallback_summary(section_cards, entity_summary, dtr_config)

    def _fallback_summary(
        self,
        section_cards: dict[str, list[dict]],
        entity_summary: dict[str, str],
        dtr_config: Optional["DTRConfig"],
    ) -> str:
        """Fallback when LLM is unavailable — template-based summary."""
        doc_type = dtr_config.display_name if dtr_config else "Document"
        parts = [f"This {doc_type} contains {sum(len(v) for v in section_cards.values())} extracted clauses"]

        sections_with_content = [k for k, v in section_cards.items() if v]
        if sections_with_content:
            parts.append(f"across {len(sections_with_content)} sections ({', '.join(sections_with_content)})")

        if entity_summary:
            key_entities = list(entity_summary.items())[:3]
            entity_str = ", ".join(f"{k}: {v}" for k, v in key_entities)
            parts.append(f". Key data: {entity_str}")

        return " ".join(parts) + "."
