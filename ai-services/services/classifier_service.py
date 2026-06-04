import math

from services.embedding_service import get_embedder
from utils.text_utils import keyword_score


class ClassifierService:
    EXEMPLARS = {
        "policy": (
            "insurance policy schedule sum insured premium exclusions waiting period coverage "
            "benefits room rent deductible co-pay renewal terms policy number"
        ),
        "claim": (
            "claim form claimant hospital admission discharge accident claim intimation "
            "settlement reimbursement documents required claim number"
        ),
        "invoice": (
            "hospital bill invoice bill number charges amount payable tax gst itemised "
            "room charges medicine procedure total"
        ),
        "medical": (
            "medical report prescription diagnosis symptoms medicine treatment doctor "
            "clinical findings disease laboratory investigation"
        ),
        "kyc": (
            "aadhaar pan card identity proof address proof kyc date of birth government "
            "identification number"
        ),
        "legal": (
            "fir police report legal notice incident accident case number station "
            "complaint statement"
        ),
    }

    RULE_TERMS = {
        "claim": ["claim form", "claimant", "date of accident", "claim no", "claim number"],
        "invoice": ["invoice", "bill no", "amount payable", "gst", "itemised bill"],
        "medical": ["prescription", "diagnosis", "medicine", "clinical", "laboratory"],
        "kyc": ["aadhaar", "pan card", "kyc", "identity proof"],
        "legal": ["fir", "police", "case number", "legal notice"],
        "policy": ["policy number", "sum insured", "premium", "exclusions", "waiting period"],
    }

    def __init__(self):
        self.embedder = get_embedder()
        self._exemplar_vectors: dict[str, list[float]] | None = None

    def classify(self, text: str, file_name: str = "") -> str:
        haystack = f"{file_name}\n{text[:6000]}".lower()
        rule = self._rule_match(haystack)
        semantic = self._semantic_match(haystack)
        return semantic or rule or "policy"

    def _rule_match(self, haystack: str) -> str | None:
        scores = {
            doc_type: sum(1 for term in terms if term in haystack)
            for doc_type, terms in self.RULE_TERMS.items()
        }
        best_type, best_score = max(scores.items(), key=lambda item: item[1])
        return best_type if best_score > 0 else None

    def _semantic_match(self, haystack: str) -> str | None:
        try:
            self._ensure_exemplars()
            query_vector = self.embedder.embed_one(haystack[:3000])
            assert self._exemplar_vectors is not None
            scored = []
            for doc_type, vector in self._exemplar_vectors.items():
                semantic = self._cosine(query_vector, vector)
                lexical = keyword_score(self.EXEMPLARS[doc_type], haystack)
                scored.append((doc_type, semantic + lexical * 0.25))
            best_type, best_score = max(scored, key=lambda item: item[1])
            return best_type if best_score >= 0.18 else None
        except Exception:
            return None

    def _ensure_exemplars(self) -> None:
        if self._exemplar_vectors is not None:
            return
        vectors = self.embedder.embed(list(self.EXEMPLARS.values()))
        self._exemplar_vectors = {
            doc_type: vector
            for doc_type, vector in zip(self.EXEMPLARS.keys(), vectors)
        }

    def _cosine(self, a: list[float], b: list[float]) -> float:
        size = min(len(a), len(b))
        if size == 0:
            return 0.0
        dot = sum(a[i] * b[i] for i in range(size))
        na = math.sqrt(sum(a[i] * a[i] for i in range(size))) or 1.0
        nb = math.sqrt(sum(b[i] * b[i] for i in range(size))) or 1.0
        return dot / (na * nb)
