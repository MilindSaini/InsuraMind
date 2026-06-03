from config import get_settings
from utils.text_utils import section_hint, topic_label


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
        if self.client and rows:
            try:
                return self._llm_answer(question, rows, intent, risk_alerts), self._confidence(rows), risk_alerts, intent
            except Exception:
                pass
        return self._extractive_answer(question, rows, risk_alerts), self._confidence(rows), risk_alerts, intent

    def _client(self):
        if not self.settings.gemini_api_key:
            return None
        try:
            from google import genai

            return genai.Client(api_key=self.settings.gemini_api_key)
        except Exception:
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

    def _extractive_answer(self, question: str, rows: list[dict], risk_alerts: list[str]) -> str:
        if not rows:
            topic = topic_label(section_hint(question))
            return f"I could not find enough direct evidence about {topic} in this document."
        top = rows[:4]
        topic = topic_label(section_hint(question))
        lines = [f"Based on the most relevant policy text I found about {topic}:"]
        for row in top:
            cite = row.get("citationLabel") or f"page {row.get('pageNumber')}"
            snippet = row.get("text", "").strip().replace("\n", " ")
            if len(snippet) > 360:
                snippet = snippet[:360].rsplit(" ", 1)[0] + "..."
            lines.append(f"- [{cite}] {snippet}")
        if risk_alerts:
            lines.append("Risk alerts: " + "; ".join(risk_alerts[:3]))
        lines.append("This is an evidence-grounded reading of the uploaded document, not a final insurer decision.")
        return "\n".join(lines)

    def _risk_alerts(self, rows: list[dict]) -> list[str]:
        alerts = []
        for row in rows:
            section = row.get("sectionType", "")
            risk = row.get("riskLevel", "")
            heading = row.get("heading") or row.get("citationLabel") or "source clause"
            if risk == "high" or section in {"exclusion", "waiting_period"}:
                alerts.append(f"{heading}: {section.replace('_', ' ')} may affect claim outcome")
        return list(dict.fromkeys(alerts))[:5]

    def _confidence(self, rows: list[dict]) -> float:
        if not rows:
            return 0.15
        score = max(float(row.get("score", 0.0)) for row in rows)
        return max(0.35, min(0.93, 0.55 + score * 0.25))
