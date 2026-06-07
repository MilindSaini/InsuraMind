import json
import re

from config import get_settings
from models.schemas import Citation
from services.embedding_service import get_embedder
from services.vector_store import VectorStore
from utils.logging import get_logger
from utils.text_utils import is_noise_text, keyword_score, section_hint

log = get_logger("services.retrieval")


class RetrievalService:
    QUERY_EXPANSION_LIMIT = 3

    def __init__(self):
        self.settings = get_settings()
        self.embedder = get_embedder()
        self.store = VectorStore()
        self.client = self._client()

    def index(self, document_id: str, user_id: str, chunks) -> None:
        vectors = self.embedder.embed([chunk.text for chunk in chunks])
        self.store.upsert(document_id, user_id, chunks, vectors)

    def retrieve(self, document_id: str, user_id: str, question: str, limit: int = 8) -> list[dict]:
        candidates: list[dict] = []
        seen: set[tuple[object, ...]] = set()
        for variant in self.expand_queries(question):
            vector = self.embedder.embed_one(variant)
            for row in self.store.search(document_id, user_id, variant, vector, limit=max(limit * 2, 10)):
                if row.get("sectionType") == "noise" or is_noise_text(row.get("text", "")):
                    continue
                key = self._row_key(row)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(row)
        return self.rank(question, candidates, limit=limit)

    def rank(self, question: str, rows: list[dict], limit: int = 8) -> list[dict]:
        if not rows:
            return []

        variants = self.expand_queries(question)
        query_vectors = [self.embedder.embed_one(variant) for variant in variants]
        hint = section_hint(question)
        ranked: list[dict] = []
        for row in rows:
            if row.get("sectionType") == "noise" or is_noise_text(row.get("text", "")):
                continue
            text = row.get("text", "")
            row_vector = self.embedder.embed_one(text) if text else []
            semantic = max((self.store._cosine(query_vector, row_vector) for query_vector in query_vectors), default=0.0) if row_vector else 0.0
            lexical = max((keyword_score(variant, text) for variant in variants), default=0.0)
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
            if section == "noise":
                continue
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
                heading=row.get("parentHeading") or row.get("heading"),
                text=row.get("text", "")[:1200],
                score=float(row.get("score", 0.0)),
            )
            for row in rows
        ]

    def expand_queries(self, question: str) -> list[str]:
        variants = [self._normalize_question(question)]
        if self.client:
            try:
                variants.extend(self._gemini_expansions(question))
            except Exception as exc:
                log.warning("retrieval.query_expansion_failed", error=str(exc))
        variants.extend(self._heuristic_expansions(question))
        return self._dedupe_variants(variants)

    def _client(self):
        if not self.settings.gemini_api_key:
            return None
        try:
            from google import genai

            return genai.Client(api_key=self.settings.gemini_api_key)
        except Exception as exc:
            log.warning("retrieval.gemini_init_failed", error=str(exc))
            return None

    def _gemini_expansions(self, question: str) -> list[str]:
        from google.genai import types

        prompt = (
            "Rewrite this insurance question into three alternative phrasings that might appear in an Indian insurance policy document. "
            "Consider IRDAI standard terminology, formal legal wording, and common policy clause headings used by Indian insurers. "
            "Include synonyms and related concepts (e.g. 'due care' → 'reasonable precautions', 'utmost good faith'). "
            "Use short clause-like wording. Return only a JSON array of strings. "
            "Do not repeat the original question verbatim.\n\n"
            f"Question: {question}"
        )
        message = self.client.models.generate_content(
            model=self.settings.gemini_fast_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=180,
            ),
        )
        text = getattr(message, "text", None) or ""
        return self._parse_variants(text)

    def _parse_variants(self, text: str) -> list[str]:
        if not text.strip():
            return []
        variants: list[str] = []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                variants = [str(item).strip() for item in parsed]
            elif isinstance(parsed, dict):
                raw = parsed.get("variants") or parsed.get("queries") or []
                if isinstance(raw, list):
                    variants = [str(item).strip() for item in raw]
        except Exception:
            variants = []
        if not variants:
            variants = [re.sub(r"^[\-\d.\)\s]+", "", line).strip() for line in text.splitlines()]
        return [variant for variant in variants if variant]

    def _heuristic_expansions(self, question: str) -> list[str]:
        q = question.lower()
        expansions: list[str] = []
        if "due care" in q:
            expansions.extend([
                "reasonable precautions",
                "duty to cooperate",
                "utmost good faith",
            ])
        if any(term in q for term in ["waiting period", "pre-existing", "ped"]):
            expansions.extend([
                "pre-existing disease waiting period",
                "ped clause",
                "initial waiting period",
            ])
        if any(term in q for term in ["claim", "reject", "repudiate", "denied"]):
            expansions.extend([
                "claim rejection clause",
                "claim settlement conditions",
                "documents required for claim",
            ])
        return expansions

    def _normalize_question(self, question: str) -> str:
        return re.sub(r"\s+", " ", question).strip(" ?!\t\n\r")

    def _dedupe_variants(self, variants: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for variant in variants:
            normalized = self._normalize_question(variant)
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(normalized)
            if len(ordered) >= self.QUERY_EXPANSION_LIMIT + 1:
                break
        return ordered

    def _row_key(self, row: dict) -> tuple[object, ...]:
        return (
            row.get("document_id"),
            row.get("user_id"),
            row.get("chunkIndex"),
            row.get("pageNumber"),
            row.get("sectionType"),
            row.get("text", "")[:120],
        )
