import json
import re
import urllib.error
import urllib.request
from typing import Optional

from config import get_settings
from dtr.models import DTRConfig


class VerifierService:
    def __init__(self):
        self.settings = get_settings()

    def verify(
        self,
        answer: str,
        rows: list[dict],
        config: Optional[DTRConfig] = None,
    ) -> bool:
        if not rows:
            return False
        if self.settings.gemini_api_key:
            result = self._gemini_verify(answer, rows, config)
            if result is not None:
                return result
        return self._local_verify(answer, rows)

    def _gemini_verify(
        self,
        answer: str,
        rows: list[dict],
        config: Optional[DTRConfig] = None,
    ) -> bool | None:
        evidence = "\n\n".join(
            f"[{row.get('citationLabel') or 'source'} | page {row.get('pageNumber')}] "
            f"{row.get('text', '')[:1600]}"
            for row in rows[:6]
        )
        doc_type_name = config.display_name if config else "insurance policy"
        prompt = (
            f"You are a strict verifier for a {doc_type_name} AI answer. "
            "Decide whether the answer is grounded only in the provided evidence. "
            "Return only compact JSON with this exact shape: "
            '{"verified": true|false, "reason": "short reason"}.\n\n'
            f"ANSWER:\n{answer}\n\nEVIDENCE:\n{evidence}"
        )
        body = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 180,
                "responseMimeType": "application/json",
            },
        }
        model = self.settings.gemini_verifier_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.settings.gemini_api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

        text = self._extract_text(payload)
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.S)
            if not match:
                return None
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        verified = parsed.get("verified")
        return verified if isinstance(verified, bool) else None

    def _extract_text(self, payload: dict) -> str:
        parts = []
        for candidate in payload.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                text = part.get("text")
                if text:
                    parts.append(text)
        return "".join(parts).strip()

    def _local_verify(self, answer: str, rows: list[dict]) -> bool:
        labels = [row.get("citationLabel") for row in rows if row.get("citationLabel")]
        if labels and any(label in answer for label in labels):
            return True
        answer_terms = set(answer.lower().split())
        evidence_terms = set(" ".join(row.get("text", "") for row in rows[:5]).lower().split())
        return len(answer_terms & evidence_terms) >= 8
