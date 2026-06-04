import re

from models.schemas import Chunk, ExtractedEntity


class ExtractorService:
    PATTERNS = {
        "policy_number": r"(policy\s*(?:no|number)[:\s-]+)([A-Z0-9/-]{5,})",
        "sum_insured": r"(sum\s*insured|coverage\s*limit)[:\s-]*(?:rs\.?|inr)?\s*([0-9,]{4,})",
        "waiting_period": r"([0-9]{1,2})\s*(months?|years?)\s*(?:waiting\s*period|for\s*pre-existing|for\s*ped)?",
        "co_pay": r"(co-?pay(?:ment)?|copay)[:\s-]*([0-9]{1,2}\s*%)",
        "deductible": r"(deductible)[:\s-]*(?:rs\.?|inr)?\s*([0-9,]+)",
        "room_rent_limit": r"(room\s*rent)[^0-9%]{0,40}([0-9]{1,3}%|[0-9,]+)",
        "insurer_name": r"(?:insurer|insurance company)[:\s-]+([A-Za-z][A-Za-z .&-]{3,80})",
        "hospital": r"(?:hospital|network hospital)[:\s-]+([A-Za-z][A-Za-z .&-]{3,80})",
    }

    DISEASES = [
        "diabetes",
        "hypertension",
        "cancer",
        "asthma",
        "cataract",
        "hernia",
        "kidney disease",
        "cardiac",
        "heart disease",
        "maternity",
    ]

    SPACY_LABELS = {
        "PERSON": "person_name",
        "ORG": "organization",
        "DATE": "date",
        "MONEY": "amount",
        "CARDINAL": "number",
    }

    def __init__(self):
        self.nlp = self._load_spacy()

    def extract(self, chunks: list[Chunk]) -> list[ExtractedEntity]:
        found: list[ExtractedEntity] = []
        seen: set[tuple[str, str]] = set()
        for chunk in chunks:
            text = chunk.text
            self._regex_extract(found, seen, text, chunk)
            self._domain_terms(found, seen, text, chunk)
            self._spacy_extract(found, seen, text, chunk)
        return found

    def _regex_extract(
        self,
        found: list[ExtractedEntity],
        seen: set[tuple[str, str]],
        text: str,
        chunk: Chunk,
    ) -> None:
        for entity_type, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, text, flags=re.I):
                value = match.group(match.lastindex or 0)
                if match.lastindex and match.lastindex >= 2:
                    value = match.group(2)
                self._add(found, seen, entity_type, value, 0.84, chunk)

    def _domain_terms(
        self,
        found: list[ExtractedEntity],
        seen: set[tuple[str, str]],
        text: str,
        chunk: Chunk,
    ) -> None:
        lower = text.lower()
        for disease in self.DISEASES:
            if disease in lower:
                self._add(found, seen, "disease", disease, 0.78, chunk)

    def _spacy_extract(
        self,
        found: list[ExtractedEntity],
        seen: set[tuple[str, str]],
        text: str,
        chunk: Chunk,
    ) -> None:
        if self.nlp is None:
            return
        try:
            doc = self.nlp(text[:3500])
        except Exception:
            return
        for ent in getattr(doc, "ents", []):
            entity_type = self.SPACY_LABELS.get(ent.label_)
            if entity_type:
                self._add(found, seen, entity_type, ent.text, 0.7, chunk)

    def _load_spacy(self):
        try:
            import spacy

            try:
                return spacy.load("en_core_web_sm")
            except Exception:
                return spacy.load("en_core_web_lg")
        except Exception:
            return None

    def _add(
        self,
        found: list[ExtractedEntity],
        seen: set[tuple[str, str]],
        entity_type: str,
        value: str,
        confidence: float,
        chunk: Chunk,
    ) -> None:
        cleaned = re.sub(r"\s+", " ", value.strip(" :;-.,"))
        key = (entity_type, cleaned.lower())
        if not cleaned or len(cleaned) < 2 or key in seen:
            return
        seen.add(key)
        found.append(
            ExtractedEntity(
                entityType=entity_type,
                entityValue=cleaned,
                confidence=confidence,
                pageNumber=chunk.pageNumber,
                sourceChunkIndex=chunk.chunkIndex,
            )
        )
