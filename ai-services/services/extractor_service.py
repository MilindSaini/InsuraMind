"""Entity extraction — DTR-driven.

When a DTR config is provided, extraction patterns are built from the
config's entity_schema (type-based regex generation). Falls back to
insurance-domain patterns when no config is supplied.
"""

import re
from typing import Optional

from dtr.models import DTRConfig, EntityField
from models.schemas import Chunk, ExtractedEntity


# ─── Type-based regex patterns ────────────────────────────────────────────────
# Each entity type maps to a regex that captures the value.

_TYPE_PATTERNS: dict[str, str] = {
    "monetary": r"(?:rs\.?|inr|₹|\$|usd)?\s*([0-9,]{3,}(?:\.\d{1,2})?)\s*(?:crore|lakh|lakhs|cr|lac)?",
    "percentage": r"([0-9]{1,3}(?:\.\d{1,2})?)\s*%",
    "duration": r"([0-9]{1,4})\s*(days?|months?|years?|weeks?)",
    "date": r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})",
    "asset": r"(?:collateral|security|property|asset|mortgage)[:\s\-]+([A-Za-z][A-Za-z0-9 ,.\-]{5,120})",
}

# ─── Legacy insurance patterns (backward compat) ─────────────────────────────

_LEGACY_PATTERNS = {
    "policy_number": r"(policy\s*(?:no|number)[:\s-]+)([A-Z0-9/-]{5,})",
    "sum_insured": r"(sum\s*insured|coverage\s*limit)[:\s-]*(?:rs\.?|inr)?\s*([0-9,]{4,})",
    "waiting_period": r"([0-9]{1,2})\s*(months?|years?)\s*(?:waiting\s*period|for\s*pre-existing|for\s*ped)?",
    "co_pay": r"(co-?pay(?:ment)?|copay)[:\s-]*([0-9]{1,2}\s*%)",
    "deductible": r"(deductible)[:\s-]*(?:rs\.?|inr)?\s*([0-9,]+)",
    "room_rent_limit": r"(room\s*rent)[^0-9%]{0,40}([0-9]{1,3}%|[0-9,]+)",
    "insurer_name": r"(?:insurer|insurance company)[:\s-]+([A-Za-z][A-Za-z .&-]{3,80})",
    "hospital": r"(?:hospital|network hospital)[:\s-]+([A-Za-z][A-Za-z .&-]{3,80})",
}

_LEGACY_DISEASES = [
    "diabetes", "hypertension", "cancer", "asthma", "cataract",
    "hernia", "kidney disease", "cardiac", "heart disease", "maternity",
]

_SPACY_LABELS = {
    "PERSON": "person_name",
    "ORG": "organization",
    "DATE": "date",
    "MONEY": "amount",
    "CARDINAL": "number",
}


class ExtractorService:
    """Extracts entities from document chunks.

    When a DTR config is provided, builds extraction patterns from the
    entity_schema. Otherwise uses legacy insurance-specific patterns.
    """

    def __init__(self):
        self.nlp = self._load_spacy()

    def extract(
        self,
        sections: list[dict],
        config: Optional[DTRConfig] = None,
    ) -> list[ExtractedEntity]:
        """Extract entities from sections using DTR config or legacy patterns."""
        found: list[ExtractedEntity] = []
        seen: set[tuple[str, str]] = set()

        patterns = self._build_patterns(config)

        for section in sections:
            text = section.get("text", "")
            self._regex_extract(found, seen, text, section, patterns)
            if not config:
                # Legacy domain terms (insurance only)
                self._domain_terms(found, seen, text, section)
            self._spacy_extract(found, seen, text, section, config)
        return found

    # ── Pattern building ──────────────────────────────────────────────────────

    def _build_patterns(
        self, config: Optional[DTRConfig]
    ) -> dict[str, str]:
        """Build extraction patterns from DTR entity_schema or use legacy."""
        if not config or not config.entity_schema:
            return dict(_LEGACY_PATTERNS)

        patterns: dict[str, str] = {}
        for entity_name, field in config.entity_schema.items():
            if field.pattern:
                # Custom regex override from DTR config
                patterns[entity_name] = field.pattern
            elif entity_name in _LEGACY_PATTERNS:
                # Use legacy robust pattern if available
                patterns[entity_name] = _LEGACY_PATTERNS[entity_name]
            elif field.type in _TYPE_PATTERNS:
                # Build context-aware pattern: look for the entity name near the value
                name_readable = entity_name.replace("_", r"[\s_-]*")
                value_pattern = _TYPE_PATTERNS[field.type]
                # Match: "entity_name" followed by separator then value
                patterns[entity_name] = (
                    rf"(?:{name_readable})[:\s\-]*{value_pattern}"
                )
            # For "text" and "asset" types, we rely on spaCy NER if not in legacy
        return patterns

    # ── Regex extraction ──────────────────────────────────────────────────────

    def _regex_extract(
        self,
        found: list[ExtractedEntity],
        seen: set[tuple[str, str]],
        text: str,
        section: dict,
        patterns: dict[str, str],
    ) -> None:
        for entity_type, pattern in patterns.items():
            for match in re.finditer(pattern, text, flags=re.I):
                value = match.group(match.lastindex or 0)
                if match.lastindex and match.lastindex >= 2:
                    value = match.group(2)
                self._add(found, seen, entity_type, value, 0.84, section)

    def _domain_terms(
        self,
        found: list[ExtractedEntity],
        seen: set[tuple[str, str]],
        text: str,
        section: dict,
    ) -> None:
        """Legacy insurance domain term extraction."""
        lower = text.lower()
        for disease in _LEGACY_DISEASES:
            if disease in lower:
                self._add(found, seen, "disease", disease, 0.78, section)

    # ── spaCy NER ─────────────────────────────────────────────────────────────

    def _spacy_extract(
        self,
        found: list[ExtractedEntity],
        seen: set[tuple[str, str]],
        text: str,
        section: dict,
        config: Optional[DTRConfig] = None,
    ) -> None:
        if self.nlp is None:
            return
        try:
            doc = self.nlp(text[:3500])
        except Exception:
            return

        # Map spaCy labels to entity types
        label_map = dict(_SPACY_LABELS)

        # If DTR config has "text" type entities, try to match NER results
        if config and config.entity_schema:
            text_entities = [
                name
                for name, field in config.entity_schema.items()
                if field.type == "text"
            ]
            # Boost extraction of ORG/PERSON for text-type entities
            for ent in getattr(doc, "ents", []):
                entity_type = label_map.get(ent.label_)
                if entity_type:
                    self._add(found, seen, entity_type, ent.text, 0.7, section)
        else:
            for ent in getattr(doc, "ents", []):
                entity_type = label_map.get(ent.label_)
                if entity_type:
                    self._add(found, seen, entity_type, ent.text, 0.7, section)

    # ── Helpers ───────────────────────────────────────────────────────────────

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
        section: dict,
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
                pageNumber=section.get("page_number"),
                sourceChunkIndex=section.get("chunk_index"),
            )
        )
