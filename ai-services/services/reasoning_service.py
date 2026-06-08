"""Reasoning / answer generation — DTR-driven.

Intent detection, answer generation, and risk alerting are all parameterized
by the DTR config.  When no config is provided, falls back to the original
insurance-focused behavior.
"""

from typing import Optional

from config import get_settings
from dtr.models import DTRConfig
from utils.logging import get_logger
from utils.text_utils import keyword_score, section_hint, topic_label

log = get_logger("services.reasoning")


class ReasoningService:
    def __init__(self):
        self.settings = get_settings()
        self.client = self._client()

    # ── Intent detection ──────────────────────────────────────────────────────

    def detect_intent(
        self, question: str, config: Optional[DTRConfig] = None
    ) -> str:
        """Classify query intent using DTR intents or legacy rules."""
        # If LLM is available and we have DTR intents, use LLM classification
        if config and config.query_intents and self.client:
            try:
                return self._llm_intent(question, config)
            except Exception as exc:
                log.warning("reasoning.llm_intent_failed", error=str(exc))

        # Keyword fallback
        if config and config.query_intents:
            return self._keyword_intent(question, config)

        # Legacy insurance fallback
        return self._legacy_intent(question)

    def _llm_intent(self, question: str, config: DTRConfig) -> str:
        """Use LLM to classify query intent against DTR intent list."""
        from google.genai import types

        intent_list = config.intent_labels()
        prompt = (
            f"You are classifying a user question about a {config.display_name}.\n"
            f"Valid intents: {intent_list}\n"
            f"Also valid: fact_lookup (general information query)\n\n"
            f"Question: {question}\n\n"
            "Return ONLY the intent name, nothing else."
        )
        message = self.client.models.generate_content(
            model=self.settings.gemini_fast_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=30,
            ),
        )
        text = (getattr(message, "text", None) or "").strip().lower()
        # Validate against known intents
        for intent in config.query_intents:
            if intent in text:
                return intent
        return "fact_lookup"

    def _keyword_intent(self, question: str, config: DTRConfig) -> str:
        """Match intents by keyword overlap with the question."""
        q = question.lower()
        best_intent = "fact_lookup"
        best_score = 0
        for intent in config.query_intents:
            # Convert intent name to readable words: "repayment_check" -> ["repayment", "check"]
            words = intent.replace("_", " ").split()
            score = sum(1 for word in words if word in q)
            if score > best_score:
                best_score = score
                best_intent = intent
        return best_intent if best_score > 0 else "fact_lookup"

    def _legacy_intent(self, question: str) -> str:
        """Legacy insurance intent detection."""
        q = question.lower()
        if any(term in q for term in ["compare", "better policy", "policy a", "policy b"]):
            return "comparison"
        if any(term in q for term in ["claim", "approved", "rejected", "eligible", "pass"]):
            return "eligibility"
        if any(term in q for term in ["risk", "hidden", "danger", "reject"]):
            return "risk_analysis"
        if any(term in q for term in ["simulate", "scenario", "what if"]):
            return "simulation"
        return "fact_lookup"

    # ── Answer generation ─────────────────────────────────────────────────────

    def answer(
        self,
        question: str,
        rows: list[dict],
        config: Optional[DTRConfig] = None,
    ) -> tuple[str, float, list[str], str]:
        """Generate an answer using DTR config for context and templates."""
        intent = self.detect_intent(question, config)
        risk_alerts = self._risk_alerts(rows, config)
        confidence = self._confidence(rows)

        if self._should_fallback_to_general_knowledge(rows, confidence, question):
            return (
                self._general_knowledge_answer(question, intent, risk_alerts, config),
                min(confidence, 0.58),
                risk_alerts,
                intent,
            )

        if self.client and rows:
            try:
                return (
                    self._llm_answer(question, rows, intent, risk_alerts, config),
                    confidence,
                    risk_alerts,
                    intent,
                )
            except Exception as exc:
                log.warning(
                    "reasoning.llm_failed",
                    intent=intent,
                    error=str(exc),
                    fallback="extractive",
                )

        return (
            self._extractive_answer(question, rows, risk_alerts, config),
            confidence,
            risk_alerts,
            intent,
        )

    # ── LLM answer ────────────────────────────────────────────────────────────

    def _llm_answer(
        self,
        question: str,
        rows: list[dict],
        intent: str,
        risk_alerts: list[str],
        config: Optional[DTRConfig] = None,
    ) -> str:
        evidence = "\n\n".join(
            f"[{row.get('citationLabel') or 'source'} | page {row.get('pageNumber')}] "
            f"{row.get('text', '')[:1400]}"
            for row in rows[:6]
        )

        # Build system prompt from DTR config
        doc_type_name = config.display_name if config else "insurance policy"
        regulatory = config.regulatory_context if config else ""

        system_prompt = (
            f"You are InsuraMind, a {doc_type_name} intelligence assistant. "
            "Answer only from the evidence. If evidence is insufficient, say so. "
            "Use plain language. Include citations like [p.4 c.2]. "
            "Do not provide legal certainty; provide document-text-based guidance."
        )
        if regulatory:
            system_prompt += f"\n\nRegulatory context: {regulatory}"

        model = (
            self.settings.gemini_reasoning_model
            if intent in {"eligibility", "comparison", "simulation", "liability_check", "obligation_check"}
            else self.settings.gemini_fast_model
        )

        prompt = (
            f"{system_prompt}\n\n"
            f"Document type: {doc_type_name}\n"
            f"Query intent: {intent}\n"
            f"Question: {question}\n\nEvidence:\n{evidence}\n\nRisk alerts: {risk_alerts}"
        )

        from google.genai import types

        message = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=900,
            ),
        )
        text = getattr(message, "text", None) or ""
        if text:
            return text.strip()
        candidates = getattr(message, "candidates", None) or []
        parts = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                part_text = getattr(part, "text", None)
                if part_text:
                    parts.append(part_text)
        return "".join(parts).strip()

    # ── General knowledge fallback ────────────────────────────────────────────

    def _general_knowledge_answer(
        self,
        question: str,
        intent: str,
        risk_alerts: list[str],
        config: Optional[DTRConfig] = None,
    ) -> str:
        if self.client:
            try:
                return self._llm_general_knowledge_answer(
                    question, intent, risk_alerts, config
                )
            except Exception as exc:
                log.warning(
                    "reasoning.general_knowledge_llm_failed",
                    intent=intent,
                    error=str(exc),
                )
        doc_type_name = config.display_name if config else "insurance policy"
        term = question.strip().rstrip("?.")
        return (
            f"General knowledge, not from your {doc_type_name.lower()}: '{term}' usually refers to a standard "
            f"clause or provision. Wording varies by document, so check the specific {doc_type_name.lower()} "
            "text or consult a professional for the exact interpretation."
        )

    def _llm_general_knowledge_answer(
        self,
        question: str,
        intent: str,
        risk_alerts: list[str],
        config: Optional[DTRConfig] = None,
    ) -> str:
        doc_type_name = config.display_name if config else "insurance policy"
        regulatory = config.regulatory_context if config else ""

        model = (
            self.settings.gemini_reasoning_model
            if intent in {"eligibility", "comparison", "simulation"}
            else self.settings.gemini_fast_model
        )

        prompt = (
            f"You are InsuraMind. The uploaded {doc_type_name.lower()} text does not appear to define the user's term. "
            "Answer from general knowledge about this type of document, not from the document itself. "
            'Start the answer with exactly: "General knowledge, not from your document:". '
            "Keep it concise, practical, and clearly say the wording can vary by document. "
            "Suggest checking the document text or consulting a professional for the exact clause."
        )
        if regulatory:
            prompt += f"\nRegulatory context: {regulatory}"
        prompt += f"\nQuestion: {question}\n\nRisk alerts: {risk_alerts}"

        from google.genai import types

        message = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=220,
            ),
        )
        text = getattr(message, "text", None) or ""
        return text.strip() or self._general_knowledge_answer(
            question, intent, risk_alerts, config
        )

    # ── Extractive fallback ───────────────────────────────────────────────────

    def _extractive_answer(
        self,
        question: str,
        rows: list[dict],
        risk_alerts: list[str],
        config: Optional[DTRConfig] = None,
    ) -> str:
        doc_type_name = config.display_name if config else "document"
        if not rows:
            topic = topic_label(section_hint(question))
            return (
                f"This term isn't defined in your {doc_type_name.lower()}. In standard practice, "
                f"{topic} is usually handled through the related clauses. "
                "Check the relevant clause or consult a professional."
            )
        top = rows[:4]
        topic = topic_label(section_hint(question))
        lines = [f"Based on the most relevant {doc_type_name.lower()} text I found about {topic}:"]
        for row in top:
            cite = row.get("citationLabel") or f"page {row.get('pageNumber')}"
            snippet = row.get("text", "").strip().replace("\n", " ")
            if len(snippet) > 360:
                snippet = snippet[:360].rsplit(" ", 1)[0] + "..."
            heading = row.get("parentHeading") or row.get("heading")
            if heading:
                lines.append(f"- {heading} — [{cite}] {snippet}")
            else:
                lines.append(f"- [{cite}] {snippet}")
        if risk_alerts:
            lines.append("Risk alerts: " + "; ".join(risk_alerts[:3]))
        lines.append(
            "This is an evidence-grounded reading of the uploaded document, "
            "not a final professional opinion."
        )
        return "\n".join(lines)

    # ── Risk alerts ───────────────────────────────────────────────────────────

    def _risk_alerts(
        self, rows: list[dict], config: Optional[DTRConfig] = None
    ) -> list[str]:
        alerts = []
        risk_pattern_labels = set()
        if config and config.risk_patterns:
            risk_pattern_labels = {p.replace("_", " ") for p in config.risk_patterns}

        for row in rows:
            if row.get("sectionType") == "noise":
                continue
            section = row.get("sectionType", "")
            risk = row.get("riskLevel", "")
            heading = (
                row.get("parentHeading")
                or row.get("heading")
                or row.get("citationLabel")
                or "source clause"
            )
            text_lower = row.get("text", "").lower()

            # DTR risk pattern matching
            for pattern in risk_pattern_labels:
                if pattern in text_lower:
                    alerts.append(f"{heading}: {pattern} detected")

            # Section-level risk
            if risk == "high":
                alerts.append(
                    f"{heading}: {section.replace('_', ' ')} may affect outcome"
                )
            elif not config and section in {"exclusion", "waiting_period"}:
                # Legacy insurance fallback
                alerts.append(
                    f"{heading}: {section.replace('_', ' ')} may affect claim outcome"
                )

        return list(dict.fromkeys(alerts))[:5]

    # ── Confidence ────────────────────────────────────────────────────────────

    def _confidence(self, rows: list[dict]) -> float:
        filtered = [row for row in rows if row.get("sectionType") != "noise"]
        if not filtered:
            return 0.15
        score = max(float(row.get("score", 0.0)) for row in filtered)
        return max(0.3, min(0.93, 0.42 + score * 0.42))

    def _should_fallback_to_general_knowledge(
        self, rows: list[dict], confidence: float, question: str = ""
    ) -> bool:
        if not rows:
            return True
        if all(row.get("sectionType") == "noise" for row in rows):
            return True
        if confidence < 0.55:
            return True
        best_score = max(float(row.get("score", 0.0)) for row in rows)
        if best_score < 0.2:
            return True
        # Relevance gate: even if cosine is high, check keyword overlap
        if question:
            best_keyword = max(
                keyword_score(question, row.get("text", ""))
                for row in rows
                if row.get("sectionType") != "noise"
            )
            if best_keyword < 0.08 and best_score < 0.5:
                return True
        return False

    # ── Gemini client ─────────────────────────────────────────────────────────

    def _client(self):
        if not self.settings.gemini_api_key:
            log.info("reasoning.gemini_disabled", reason="GEMINI_API_KEY not set")
            return None
        try:
            from google import genai

            client = genai.Client(api_key=self.settings.gemini_api_key)
            log.info("reasoning.gemini_ready", model=self.settings.gemini_fast_model)
            return client
        except Exception as exc:
            log.warning("reasoning.gemini_init_failed", error=str(exc))
            return None
