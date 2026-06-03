class VerifierService:
    def verify(self, answer: str, rows: list[dict]) -> bool:
        if not rows:
            return False
        labels = [row.get("citationLabel") for row in rows if row.get("citationLabel")]
        if labels and any(label in answer for label in labels):
            return True
        answer_terms = set(answer.lower().split())
        evidence_terms = set(" ".join(row.get("text", "") for row in rows[:5]).lower().split())
        return len(answer_terms & evidence_terms) >= 8
