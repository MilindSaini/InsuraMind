import hashlib
import math
from functools import lru_cache

from config import get_settings
from utils.logging import get_logger
from utils.text_utils import words

log = get_logger("services.embedding")


class EmbeddingService:
    def __init__(self):
        self.settings = get_settings()
        self._model = self._load_model()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._model is not None:
            try:
                vectors = self._model.encode(texts, normalize_embeddings=True)
                return [list(map(float, vector)) for vector in vectors]
            except Exception as exc:
                log.warning("embedding.model_failed", error=str(exc), fallback="hash_embedding")
        return [self._hash_embedding(text) for text in texts]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def dimension(self) -> int:
        return self.settings.embedding_dim

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(self.settings.embedding_model)
            log.info("embedding.model_loaded", model=self.settings.embedding_model)
            return model
        except Exception as exc:
            log.warning(
                "embedding.model_load_failed",
                model=self.settings.embedding_model,
                error=str(exc),
                fallback="hash_embedding",
            )
            return None

    def _hash_embedding(self, text: str) -> list[float]:
        dim = self.settings.embedding_dim
        vector = [0.0] * dim
        for token in words(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % dim
            sign = -1.0 if digest[4] % 2 else 1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


@lru_cache
def get_embedder() -> EmbeddingService:
    return EmbeddingService()
