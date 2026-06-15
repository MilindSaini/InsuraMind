"""Unified per-section processor — runs the full extraction pipeline on a single section.

Pipeline per section:
  1. Rules + spaCy first  →  extract entities + build preliminary clauses
  2. Confidence gate      →  skip LLM if confident
  3. Clause hash cache    →  skip if already cached
  4. LLM gap-fill         →  Gemini Flash only for low-confidence gaps
  5. Risk tagging         →  rule-based first, LLM only for ambiguous
  6. Cache store          →  save extraction result

This replaces the old separate stages: ClauseExtractorStage, RiskTaggerStage,
EntityExtractorStage, and InsightRefinerStage.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import TYPE_CHECKING, Optional

from config import get_settings
from services.clause_cache import ClauseCache, compute_clause_hash
from services.confidence_gate import should_skip_llm
from utils.logging import get_logger

if TYPE_CHECKING:
    from dtr.models import DTRConfig

log = get_logger("services.section_processor")

# ─── Risk pattern keywords (rule-based, per DTR risk_patterns) ───────────────

_RISK_KEYWORDS: dict[str, list[str]] = {
    "high": [
        "exclusion", "not covered", "excluded", "penalty", "forfeiture",
        "default", "acceleration", "unlimited liability", "unilateral",
        "hidden", "trap", "excessive", "no option", "blanket lien",
    ],
    "medium": [
        "waiting period", "pre-existing", "sub-limit", "deductible",
        "co-pay", "conditions apply", "subject to", "at discretion",
        "floating rate", "lock-in", "restriction",
    ],
}


class SectionProcessor:
    """Processes a single document section through the full extraction pipeline."""

    def __init__(self):
        self.settings = get_settings()
        self._extractor = None
        self._cache = ClauseCache()
        self._gemini_client = None

    @property
    def extractor(self):
        """Lazy-load the existing ExtractorService (regex + spaCy)."""
        if self._extractor is None:
            from services.extractor_service import ExtractorService
            self._extractor = ExtractorService()
        return self._extractor

    def _get_gemini_client(self):
        if self._gemini_client is None:
            if self.settings.gemini_api_key:
                try:
                    from google import genai
                    self._gemini_client = genai.Client(api_key=self.settings.gemini_api_key)
                except Exception as exc:
                    log.warning("section_processor.gemini_init_failed", error=str(exc))
        return self._gemini_client

    async def process(
        self,
        section: dict,
        dtr_config: Optional["DTRConfig"] = None,
    ) -> dict:
        """Process a single section → return structured extraction result.

        Returns:
            dict with keys: clauses, entities, llm_skipped, cache_hit
        """
        section_text = section.get("text", "")
        section_type = section.get("section_type", "general")
        doc_type = dtr_config.doc_type if dtr_config else "unknown"

        # Skip noise sections entirely
        if section_type == "noise":
            return {"clauses": [], "entities": [], "llm_skipped": True, "cache_hit": False}

        # ── Step 1: Check clause hash cache ──────────────────────────────────
        clause_hash = compute_clause_hash(
            section_text, doc_type, self.settings.extractor_version
        )
        cached = await self._cache.get_cached(clause_hash)
        if cached is not None:
            log.info(
                "section_processor.cache_hit",
                section_type=section_type,
                hash=clause_hash[:12],
            )
            # Extract entities from cached clauses
            entities = []
            for c in cached:
                entities.extend(c.get("entities", []))
            return {
                "clauses": cached,
                "entities": entities,
                "llm_skipped": True,
                "cache_hit": True,
            }

        # ── Step 2: Rules + spaCy extraction ─────────────────────────────────
        rule_clauses, rule_entities = await self._rules_spacy_extract(
            section, dtr_config
        )

        # ── Step 3: Confidence gate ──────────────────────────────────────────
        entity_dicts = [
            {"entityType": e.entityType, "entityValue": e.entityValue, "confidence": e.confidence}
            for e in rule_entities
        ]
        clause_dicts = [
            {"confidence": c.get("confidence", 0.0), **c}
            for c in rule_clauses
        ]

        skip_llm = should_skip_llm(
            clause_dicts,
            entity_dicts,
            section_type,
            dtr_config,
            threshold=self.settings.confidence_skip_threshold,
        )

        if skip_llm:
            # Finalize with rule-based risk tagging
            final_clauses = self._apply_rule_risk_tags(rule_clauses, dtr_config)
            final_clauses = self._finalize_clauses(
                final_clauses, clause_hash, section_type, section,
                rule_entities, method="rules_spacy"
            )
            # Cache the result
            await self._cache.put_cached(clause_hash, final_clauses)
            return {
                "clauses": final_clauses,
                "entities": [e.model_dump() for e in rule_entities],
                "llm_skipped": True,
                "cache_hit": False,
            }

        # ── Step 4: LLM gap-fill (Gemini Flash) ─────────────────────────────
        llm_clauses = await self._llm_gap_fill(section, rule_clauses, dtr_config)

        # Merge: LLM clauses supplement rule-based ones
        merged_clauses = self._merge_clauses(rule_clauses, llm_clauses)

        # ── Step 5: Risk tagging ─────────────────────────────────────────────
        tagged_clauses = self._apply_rule_risk_tags(merged_clauses, dtr_config)

        # ── Step 6: Finalize and cache ───────────────────────────────────────
        final_clauses = self._finalize_clauses(
            tagged_clauses, clause_hash, section_type, section,
            rule_entities, method="llm"
        )
        await self._cache.put_cached(clause_hash, final_clauses)

        return {
            "clauses": final_clauses,
            "entities": [e.model_dump() for e in rule_entities],
            "llm_skipped": False,
            "cache_hit": False,
        }

    # ── Rules + spaCy extraction ──────────────────────────────────────────────

    async def _rules_spacy_extract(
        self,
        section: dict,
        dtr_config: Optional["DTRConfig"],
    ) -> tuple[list[dict], list]:
        """Run regex patterns + spaCy NER on a section.

        Returns (preliminary_clauses, extracted_entities).
        """
        from models.schemas import ExtractedEntity

        text = section.get("text", "")
        section_type = section.get("section_type", "general")
        heading = section.get("heading") or ""

        # Use the existing ExtractorService for regex + spaCy
        # Build a minimal clause wrapper for compatibility
        pseudo_clauses = [{
            "value": text,
            "source_section": section,
            "type": section_type.upper(),
            "title": heading,
        }]

        entities = await asyncio.to_thread(
            self.extractor.extract, pseudo_clauses, dtr_config
        )

        # Keep full text (capped at 3000 chars to avoid token explosion)
        full_text = text[:3000]
        # Build a clean summary trimmed at sentence boundary for card previews
        summary = self._smart_summary(text, max_len=400)

        # Build preliminary clauses from the entities found
        preliminary_clauses = []
        if entities:
            # Group entities into a clause
            clause = {
                "type": section_type.upper(),
                "title": heading or section_type.replace("_", " ").title(),
                "value": summary,
                "full_text": full_text,
                "confidence": sum(e.confidence for e in entities) / len(entities),
                "entities_found": len(entities),
            }
            preliminary_clauses.append(clause)
        else:
            # Even without entities, create a clause from the section text
            preliminary_clauses.append({
                "type": section_type.upper(),
                "title": heading or section_type.replace("_", " ").title(),
                "value": summary,
                "full_text": full_text,
                "confidence": 0.3,  # Low confidence — no entities extracted
                "entities_found": 0,
            })

        return preliminary_clauses, entities

    # ── LLM gap-fill ──────────────────────────────────────────────────────────

    async def _llm_gap_fill(
        self,
        section: dict,
        existing_clauses: list[dict],
        dtr_config: Optional["DTRConfig"],
    ) -> list[dict]:
        """Call Gemini Flash only for fields that couldn't be extracted by rules."""
        client = self._get_gemini_client()
        if client is None:
            return []

        section_type = section.get("section_type", "general")
        text = section.get("text", "")

        # Build context about what we already have
        already_extracted = []
        for c in existing_clauses:
            already_extracted.append(f"- {c.get('title', '')}: {c.get('value', '')[:100]}")
        existing_context = "\n".join(already_extracted) if already_extracted else "None"

        # Build entity schema context from DTR
        entity_hints = ""
        if dtr_config and dtr_config.entity_schema:
            hints = [f"- {name} ({field.type})" for name, field in dtr_config.entity_schema.items()]
            entity_hints = f"\nExpected entity types:\n" + "\n".join(hints)

        prompt = f"""You are an expert document extraction AI. Extract specific clauses from the text below.
Focus ONLY on information NOT already captured below.

Section Type: {section_type}
Already Extracted:
{existing_context}
{entity_hints}

Text:
{text}

Return ONLY a JSON array of objects with:
- "type": clause type (e.g., "{section_type.upper()}")
- "title": short 2-4 word title
- "value": the extracted value, amount, or concise summary

If no additional meaningful clauses exist, return an empty array [].
"""
        try:
            from google.genai import types

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.settings.gemini_fast_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                    max_output_tokens=2048,
                ),
            )
            raw_text = getattr(response, "text", None) or ""
            data = json.loads(raw_text)
            if isinstance(data, list):
                for item in data:
                    item["confidence"] = 0.85  # LLM extraction confidence
                return data
            return []
        except Exception as exc:
            log.warning("section_processor.llm_gap_fill_failed", error=str(exc))
            return []

    # ── Merging ───────────────────────────────────────────────────────────────

    def _merge_clauses(
        self,
        rule_clauses: list[dict],
        llm_clauses: list[dict],
    ) -> list[dict]:
        """Merge rule-based and LLM clauses, preferring LLM for new info."""
        merged = list(rule_clauses)
        existing_titles = {c.get("title", "").lower() for c in rule_clauses}

        for llm_clause in llm_clauses:
            title = llm_clause.get("title", "").lower()
            if title and title not in existing_titles:
                merged.append(llm_clause)
                existing_titles.add(title)

        return merged

    # ── Risk tagging (rule-based) ─────────────────────────────────────────────

    def _apply_rule_risk_tags(
        self,
        clauses: list[dict],
        dtr_config: Optional["DTRConfig"],
    ) -> list[dict]:
        """Apply rule-based risk tagging using keyword matching."""
        # Build risk patterns from DTR config
        dtr_risk_terms = set()
        if dtr_config and dtr_config.risk_patterns:
            for pattern in dtr_config.risk_patterns:
                dtr_risk_terms.update(pattern.replace("_", " ").split())

        for clause in clauses:
            text_lower = (clause.get("value", "") + " " + clause.get("title", "")).lower()

            # Check high-risk keywords
            high_matches = sum(1 for kw in _RISK_KEYWORDS["high"] if kw in text_lower)
            med_matches = sum(1 for kw in _RISK_KEYWORDS["medium"] if kw in text_lower)
            dtr_matches = sum(1 for term in dtr_risk_terms if term in text_lower)

            if high_matches >= 2 or (high_matches >= 1 and dtr_matches >= 1):
                clause["risk_level"] = "high"
                clause["risk_score"] = min(8.0 + high_matches, 10.0)
            elif high_matches >= 1 or med_matches >= 2:
                clause["risk_level"] = "medium"
                clause["risk_score"] = 4.0 + high_matches + med_matches * 0.5
            else:
                clause["risk_level"] = "low"
                clause["risk_score"] = max(med_matches * 1.5, 0.0)

            clause["risk_reason"] = self._risk_reason(text_lower, dtr_config)

        return clauses

    def _risk_reason(self, text_lower: str, dtr_config: Optional["DTRConfig"]) -> str:
        """Generate a human-readable risk reason from matched patterns."""
        reasons = []
        if dtr_config and dtr_config.risk_patterns:
            for pattern in dtr_config.risk_patterns:
                readable = pattern.replace("_", " ")
                if any(word in text_lower for word in readable.split()):
                    reasons.append(readable)
        if not reasons:
            for level_keywords in _RISK_KEYWORDS.values():
                for kw in level_keywords:
                    if kw in text_lower:
                        reasons.append(kw)
        return "; ".join(reasons[:3]) if reasons else ""

    # ── Finalize ──────────────────────────────────────────────────────────────

    def _finalize_clauses(
        self,
        clauses: list[dict],
        clause_hash: str,
        section_type: str,
        section: dict,
        entities: list,
        method: str,
    ) -> list[dict]:
        """Attach metadata to finalized clauses."""
        result = []
        for clause in clauses:
            final = {
                "clause_hash": clause_hash,
                "clause_type": section_type,
                "title": clause.get("title", ""),
                "value": clause.get("value", ""),
                "full_text": clause.get("full_text", clause.get("value", "")),
                "entities": [e.model_dump() if hasattr(e, "model_dump") else e for e in entities],
                "confidence": clause.get("confidence", 0.5),
                "extraction_method": method,
                "risk_level": clause.get("risk_level", "low"),
                "risk_score": clause.get("risk_score", 0.0),
                "risk_reason": clause.get("risk_reason", ""),
                "source_section": {
                    "chunk_index": section.get("chunk_index"),
                    "section_type": section_type,
                    "heading": section.get("heading"),
                    "page_number": section.get("page_number"),
                },
            }
            result.append(final)
        return result

    # ── Smart summary ─────────────────────────────────────────────────────────

    @staticmethod
    def _smart_summary(text: str, max_len: int = 400) -> str:
        """Trim text at a sentence boundary without cutting mid-word."""
        if len(text) <= max_len:
            return text
        # Find the last sentence-ending punctuation within the limit
        truncated = text[:max_len]
        last_period = max(truncated.rfind(". "), truncated.rfind(".\n"))
        if last_period > max_len // 2:
            return truncated[: last_period + 1]
        # Fallback: trim at the last space
        last_space = truncated.rfind(" ")
        if last_space > max_len // 2:
            return truncated[:last_space] + "..."
        return truncated + "..."
