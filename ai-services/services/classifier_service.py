"""Document classifier — DTR-driven.

Classifies documents by matching against all registered DTR configs.
Uses both embedding-similarity and keyword-rule matching, with exemplars
and terms loaded from DTR configs instead of hardcoded constants.
"""

import math

from dtr.models import DTRConfig
from dtr.registry import get_registry
from services.embedding_service import get_embedder
from utils.text_utils import keyword_score


class ClassifierService:
    """Classifies documents into DTR doc_type keys.

    Loading priority for exemplars / terms:
      1. DTR registry (from DB or Redis cache)
      2. Seed configs (hardcoded fallback)
    """

    def __init__(self):
        self.embedder = get_embedder()
        self._exemplar_vectors: dict[str, list[float]] | None = None
        self._configs: dict[str, DTRConfig] | None = None

    def classify(self, text: str, file_name: str = "") -> str:
        """Classify a document and return its DTR doc_type key."""
        self._ensure_configs()
        haystack = f"{file_name}\n{text[:6000]}".lower()
        rule = self._rule_match(haystack)
        semantic = self._semantic_match(haystack)
        return semantic or rule or "insurance_policy"

    def _rule_match(self, haystack: str) -> str | None:
        """Match against classifier_terms from all DTR configs."""
        assert self._configs is not None
        scores: dict[str, int] = {}
        for doc_type, config in self._configs.items():
            scores[doc_type] = sum(1 for term in config.classifier_terms if term in haystack)
        best_type, best_score = max(scores.items(), key=lambda item: item[1])
        return best_type if best_score > 0 else None

    def _semantic_match(self, haystack: str) -> str | None:
        """Match against classifier_exemplar embeddings from all DTR configs."""
        try:
            self._ensure_exemplar_vectors()
            query_vector = self.embedder.embed_one(haystack[:3000])
            assert self._exemplar_vectors is not None and self._configs is not None
            scored = []
            for doc_type, vector in self._exemplar_vectors.items():
                semantic = self._cosine(query_vector, vector)
                exemplar_text = self._configs[doc_type].classifier_exemplar
                lexical = keyword_score(exemplar_text, haystack)
                scored.append((doc_type, semantic + lexical * 0.25))
            best_type, best_score = max(scored, key=lambda item: item[1])
            return best_type if best_score >= 0.18 else None
        except Exception:
            return None

    # ── Lazy loading ──────────────────────────────────────────────────────────

    def _ensure_configs(self) -> None:
        """Load DTR configs from registry on first call."""
        if self._configs is not None:
            return
        registry = get_registry()
        all_configs = registry.get_all()
        self._configs = {c.doc_type: c for c in all_configs if c.classifier_exemplar}

    def _ensure_exemplar_vectors(self) -> None:
        """Build exemplar embedding vectors on first classify call."""
        if self._exemplar_vectors is not None:
            return
        self._ensure_configs()
        assert self._configs is not None
        exemplar_texts = [c.classifier_exemplar for c in self._configs.values()]
        if not exemplar_texts:
            self._exemplar_vectors = {}
            return
        vectors = self.embedder.embed(exemplar_texts)
        self._exemplar_vectors = {
            doc_type: vector
            for doc_type, vector in zip(self._configs.keys(), vectors)
        }

    # ── Math ──────────────────────────────────────────────────────────────────

    def _cosine(self, a: list[float], b: list[float]) -> float:
        size = min(len(a), len(b))
        if size == 0:
            return 0.0
        dot = sum(a[i] * b[i] for i in range(size))
        na = math.sqrt(sum(a[i] * a[i] for i in range(size))) or 1.0
        nb = math.sqrt(sum(b[i] * b[i] for i in range(size))) or 1.0
        return dot / (na * nb)
