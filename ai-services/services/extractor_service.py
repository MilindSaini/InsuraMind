import re
from models.schemas import Chunk, ExtractedEntity


class ExtractorService:
    PATTERNS = {
        "policy_number": r"(policy\s*(?:no|number)[:\s-]+)([A-Z0-9/-]{5,})",
        "sum_insured": r"(sum\s*insured|coverage\s*limit)[:\s-]*(?:rs\.?|inr|₹)?\s*([0-9,]{4,})",
        "waiting_period": r"([0-9]{1,2})\s*(months?|years?)\s*(?:waiting\s*period|for\s*pre-existing|for\s*ped)?",
        "co_pay": r"(co-?pay(?:ment)?|copay)[:\s-]*([0-9]{1,2}\s*%)",
        "deductible": r"(deductible)[:\s-]*(?:rs\.?|inr|₹)?\s*([0-9,]+)",
        "room_rent_limit": r"(room\s*rent)[^0-9%₹]{0,40}([0-9]{1,3}%|₹?\s*[0-9,]+)",
    }

    DISEASES = [
        "diabetes",
        "hypertension",
        "cancer",
        "asthma",
        "cataract",
        "hernia",
        "kidney",
        "cardiac",
        "heart disease",
    ]

    def extract(self, chunks: list[Chunk]) -> list[ExtractedEntity]:
        found: list[ExtractedEntity] = []
        seen: set[tuple[str, str]] = set()
        for chunk in chunks:
            text = chunk.text
            for entity_type, pattern in self.PATTERNS.items():
                for match in re.finditer(pattern, text, flags=re.I):
                    value = match.group(match.lastindex or 0)
                    if match.lastindex and match.lastindex >= 2:
                        value = match.group(2)
                    self._add(found, seen, entity_type, value, 0.82, chunk)
            lower = text.lower()
            for disease in self.DISEASES:
                if disease in lower:
                    self._add(found, seen, "disease", disease, 0.75, chunk)
        return found

    def _add(
        self,
        found: list[ExtractedEntity],
        seen: set[tuple[str, str]],
        entity_type: str,
        value: str,
        confidence: float,
        chunk: Chunk,
    ) -> None:
        cleaned = value.strip(" :;-.,")
        key = (entity_type, cleaned.lower())
        if not cleaned or key in seen:
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
