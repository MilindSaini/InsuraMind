from models.schemas import Citation
from services.embedding_service import get_embedder
from services.vector_store import VectorStore
from utils.text_utils import keyword_score, section_hint


class RetrievalService:
    def __init__(self):
        self.embedder = get_embedder()
        self.store = VectorStore()

    def index(self, document_id: str, user_id: str, chunks) -> None:
        vectors = self.embedder.embed([chunk.text for chunk in chunks])
        self.store.upsert(document_id, user_id, chunks, vectors)

    def retrieve(self, document_id: str, user_id: str, question: str, limit: int = 8) -> list[dict]:
        vector = self.embedder.embed_one(question)
        return self.store.search(document_id, user_id, question, vector, limit=limit)

    def rank(self, question: str, rows: list[dict], limit: int = 8) -> list[dict]:
        if not rows:
            return []

        query_vector = self.embedder.embed_one(question)
        hint = section_hint(question)
        ranked: list[dict] = []
        for row in rows:
            text = row.get("text", "")
            row_vector = self.embedder.embed_one(text) if text else []
            semantic = self.store._cosine(query_vector, row_vector) if row_vector else 0.0
            lexical = keyword_score(question, text)
            score = semantic + lexical * 0.4
            if hint and row.get("sectionType") == hint:
                score += 0.6
            elif hint and hint == "coverage" and any(term in text.lower() for term in ["covered", "benefit", "sum insured", "payable"]):
                score += 0.2
            ranked.append({"score": score, **row})

        ranked.sort(key=lambda item: item.get("score", 0), reverse=True)
        return self._diversify(ranked, hint, limit)

    def _diversify(self, rows: list[dict], hint: str | None, limit: int) -> list[dict]:
        selected: list[dict] = []
        seen: set[str] = set()

        if hint:
            for row in rows:
                if row.get("sectionType") == hint:
                    selected.append(row)
                    seen.add(hint)
                    break

        for row in rows:
            section = row.get("sectionType") or "general"
            if section in seen:
                continue
            selected.append(row)
            seen.add(section)
            if len(selected) >= limit:
                return selected[:limit]

        for row in rows:
            if row not in selected:
                selected.append(row)
            if len(selected) >= limit:
                break
        return selected[:limit]

    def citations(self, rows: list[dict]) -> list[Citation]:
        return [
            Citation(
                citationLabel=row.get("citationLabel"),
                pageNumber=row.get("pageNumber"),
                sectionType=row.get("sectionType", "general"),
                text=row.get("text", "")[:1200],
                score=float(row.get("score", 0.0)),
            )
            for row in rows
        ]
