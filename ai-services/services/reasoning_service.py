from config import get_settings
from utils.logging import get_logger
from utils.text_utils import keyword_score, section_hint, topic_label

log = get_logger("services.reasoning")


class ReasoningService:
    def __init__(self):
        self.settings = get_settings()
        self.client = self._client()

    def detect_intent(self, question: str) -> str:
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

    def answer(self, question: str, rows: list[dict]) -> tuple[str, float, list[str], str]:
        intent = self.detect_intent(question)
        risk_alerts = self._risk_alerts(rows)
        confidence = self._confidence(rows)
        if self._should_fallback_to_general_knowledge(rows, confidence, question):
            return self._general_knowledge_answer(question, intent, risk_alerts), min(confidence, 0.58), risk_alerts, intent
        if self.client and rows:
            try:
                return self._llm_answer(question, rows, intent, risk_alerts), confidence, risk_alerts, intent
            except Exception as exc:
                log.warning("reasoning.llm_failed", intent=intent, error=str(exc), fallback="extractive")
        return self._extractive_answer(question, rows, risk_alerts), confidence, risk_alerts, intent

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

    def _llm_answer(self, question: str, rows: list[dict], intent: str, risk_alerts: list[str]) -> str:
        evidence = "\n\n".join(
            f"[{row.get('citationLabel') or 'source'} | page {row.get('pageNumber')}] "
            f"{row.get('text', '')[:1400]}"
            for row in rows[:6]
        )
        model = self.settings.gemini_reasoning_model if intent in {"eligibility", "comparison", "simulation"} else self.settings.gemini_fast_model
        prompt = (
            "You are InsuraMind, an insurance policy intelligence assistant. "
            "Answer only from the evidence. If evidence is insufficient, say so. "
            "Use plain language. Include citations like [p.4 c.2]. "
            "Do not provide legal certainty; provide policy-text-based guidance.\n\n"
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

    def _general_knowledge_answer(self, question: str, intent: str, risk_alerts: list[str]) -> str:
        if self.client:
            try:
                return self._llm_general_knowledge_answer(question, intent, risk_alerts)
            except Exception as exc:
                log.warning("reasoning.general_knowledge_llm_failed", intent=intent, error=str(exc))
        term = question.strip().rstrip("?.")
        return (
            f"General knowledge, not from your policy: '{term}' usually refers to a duty to act reasonably, "
            "take ordinary precautions, and cooperate with the insurer. Wording varies by insurer, so check the policy conditions "
            "or ask your insurer for the exact clause."
        )

    def _llm_general_knowledge_answer(self, question: str, intent: str, risk_alerts: list[str]) -> str:
        model = self.settings.gemini_reasoning_model if intent in {"eligibility", "comparison", "simulation"} else self.settings.gemini_fast_model
        prompt = (
            "You are InsuraMind. The uploaded policy text does not appear to define the user's term. "
            "Answer from general insurance knowledge, not from the policy. Start the answer with exactly: "
            '"General knowledge, not from your policy:". '
            "Keep it concise, practical, and clearly say the wording can vary by insurer. "
            "Suggest checking the policy conditions or asking the insurer for the exact clause. "
            f"Question: {question}\n\nRisk alerts: {risk_alerts}"
        )
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
        return text.strip() or self._general_knowledge_answer(question, intent, risk_alerts)

    def _extractive_answer(self, question: str, rows: list[dict], risk_alerts: list[str]) -> str:
        if not rows:
            topic = topic_label(section_hint(question))
            return (
                f"This term isn't defined in your policy. In standard insurance practice, {topic} is usually handled through the related policy clauses. "
                "Check the relevant clause or ask your insurer."
            )
        top = rows[:4]
        topic = topic_label(section_hint(question))
        lines = [f"Based on the most relevant policy text I found about {topic}:"]
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
        lines.append("This is an evidence-grounded reading of the uploaded document, not a final insurer decision.")
        return "\n".join(lines)

    def _risk_alerts(self, rows: list[dict]) -> list[str]:
        alerts = []
        for row in rows:
            if row.get("sectionType") == "noise":
                continue
            section = row.get("sectionType", "")
            risk = row.get("riskLevel", "")
            heading = row.get("parentHeading") or row.get("heading") or row.get("citationLabel") or "source clause"
            if risk == "high" or section in {"exclusion", "waiting_period"}:
                alerts.append(f"{heading}: {section.replace('_', ' ')} may affect claim outcome")
        return list(dict.fromkeys(alerts))[:5]

    def _confidence(self, rows: list[dict]) -> float:
        filtered = [row for row in rows if row.get("sectionType") != "noise"]
        if not filtered:
            return 0.15
        score = max(float(row.get("score", 0.0)) for row in filtered)
        return max(0.3, min(0.93, 0.42 + score * 0.42))

    def _should_fallback_to_general_knowledge(self, rows: list[dict], confidence: float, question: str = "") -> bool:
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
        # Prevents fetching chunks that are semantically adjacent but off-topic
        if question:
            best_keyword = max(
                keyword_score(question, row.get("text", ""))
                for row in rows if row.get("sectionType") != "noise"
            )
            if best_keyword < 0.08 and best_score < 0.5:
                return True
        return False
