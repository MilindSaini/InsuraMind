import json
import math
from pathlib import Path
from typing import Any
from uuid import uuid4

from config import get_settings
from models.schemas import Chunk
from utils.logging import get_logger
from utils.text_utils import is_noise_text, keyword_score, section_hint

log = get_logger("services.vector_store")


class VectorStore:
    def __init__(self):
        self.settings = get_settings()
        self.client = self._qdrant_client()
        self.collection_ready = False

    def upsert(self, document_id: str, user_id: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if self.client:
            try:
                self._ensure_collection(len(vectors[0]) if vectors else self.settings.embedding_dim)
                self._qdrant_upsert(document_id, user_id, chunks, vectors)
                return
            except Exception as exc:
                log.warning("vector_store.qdrant_upsert_failed", error=str(exc), fallback="file_index")
        self._fallback_upsert(document_id, user_id, chunks, vectors)

    def search(self, document_id: str, user_id: str, query: str, vector: list[float], limit: int = 8) -> list[dict[str, Any]]:
        if self.client:
            try:
                self._ensure_collection(len(vector))
                return self._qdrant_search(document_id, user_id, query, vector, limit)
            except Exception as exc:
                log.warning("vector_store.qdrant_search_failed", error=str(exc), fallback="file_index")
        return self._fallback_search(document_id, user_id, query, vector, limit)

    def _qdrant_client(self):
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url=self.settings.qdrant_url)
            log.info("vector_store.qdrant_connected", url=self.settings.qdrant_url)
            return client
        except Exception as exc:
            log.warning("vector_store.qdrant_unavailable", error=str(exc), fallback="file_index")
            return None

    def _ensure_collection(self, vector_size: int) -> None:
        if self.collection_ready or not self.client:
            return
        from qdrant_client.models import Distance, VectorParams

        existing = [c.name for c in self.client.get_collections().collections]
        if self.settings.qdrant_collection not in existing:
            self.client.create_collection(
                collection_name=self.settings.qdrant_collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        self.collection_ready = True

    def _qdrant_upsert(self, document_id: str, user_id: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        from qdrant_client.models import PointStruct

        points = []
        for chunk, vector in zip(chunks, vectors):
            points.append(
                PointStruct(
                    id=str(uuid4()),
                    vector=vector,
                    payload={
                        "document_id": document_id,
                        "user_id": user_id,
                        "parent_heading": chunk.parentHeading or chunk.heading,
                        **chunk.model_dump(),
                    },
                )
            )
        self.client.upsert(collection_name=self.settings.qdrant_collection, points=points)

    def _qdrant_search(self, document_id: str, user_id: str, query: str, vector: list[float], limit: int) -> list[dict[str, Any]]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        results = self.client.search(
            collection_name=self.settings.qdrant_collection,
            query_vector=vector,
            query_filter=Filter(
                must=[
                    FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                    FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                ]
            ),
            limit=max(20, limit),
        )
        ranked = []
        hint = section_hint(query)
        for item in results:
            payload = item.payload or {}
            text = payload.get("text", "")
            if payload.get("sectionType") == "noise" or is_noise_text(text):
                continue
            score = float(item.score) + keyword_score(query, text) * 0.25
            if hint and payload.get("sectionType") == hint:
                score += 0.45
            elif hint and hint == "coverage" and any(term in text.lower() for term in ["covered", "benefit", "sum insured", "payable"]):
                score += 0.15
            ranked.append({"score": score, **payload})
        return self._diversify(sorted(ranked, key=lambda x: x["score"], reverse=True), hint, limit)

    def _fallback_upsert(self, document_id: str, user_id: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        path = Path(self.settings.fallback_index_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._load_fallback(path)
        data = [
            row for row in data
            if not (row.get("document_id") == document_id and row.get("user_id") == user_id)
        ]
        for chunk, vector in zip(chunks, vectors):
            data.append({
                "document_id": document_id,
                "user_id": user_id,
                "vector": vector,
                **chunk.model_dump(),
            })
        path.write_text(json.dumps(data), encoding="utf-8")

    def _fallback_search(self, document_id: str, user_id: str, query: str, vector: list[float], limit: int) -> list[dict[str, Any]]:
        rows = [
            row for row in self._load_fallback(Path(self.settings.fallback_index_path))
            if row.get("document_id") == document_id and row.get("user_id") == user_id
        ]
        hint = section_hint(query)
        for row in rows:
            if row.get("sectionType") == "noise" or is_noise_text(row.get("text", "")):
                continue
            semantic = self._cosine(vector, row.get("vector", []))
            lexical = keyword_score(query, row.get("text", ""))
            score = semantic + lexical * 0.35
            if hint and row.get("sectionType") == hint:
                score += 0.45
            elif hint and hint == "coverage" and any(term in row.get("text", "").lower() for term in ["covered", "benefit", "sum insured", "payable"]):
                score += 0.15
            row["score"] = score
        return self._diversify(sorted(rows, key=lambda x: x.get("score", 0), reverse=True), hint, limit)

    def _diversify(self, rows: list[dict[str, Any]], hint: str | None, limit: int) -> list[dict[str, Any]]:
        if not rows:
            return []

        selected: list[dict[str, Any]] = []
        seen_sections: set[str] = set()

        if hint:
            for row in rows:
                if row.get("sectionType") == hint:
                    selected.append(row)
                    seen_sections.add(hint)
                    break

        for row in rows:
            section = row.get("sectionType") or "general"
            if section == "noise":
                continue
            if section in seen_sections:
                continue
            selected.append(row)
            seen_sections.add(section)
            if len(selected) >= limit:
                return selected[:limit]

        for row in rows:
            if row not in selected:
                selected.append(row)
            if len(selected) >= limit:
                break
        return selected[:limit]

    def _load_fallback(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("vector_store.fallback_load_failed", path=str(path), error=str(exc))
            return []

    def _cosine(self, a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        size = min(len(a), len(b))
        dot = sum(a[i] * b[i] for i in range(size))
        na = math.sqrt(sum(a[i] * a[i] for i in range(size))) or 1.0
        nb = math.sqrt(sum(b[i] * b[i] for i in range(size))) or 1.0
        return dot / (na * nb)
