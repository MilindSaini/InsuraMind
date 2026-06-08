"""DTR Pydantic models — the single config object that every pipeline stage consumes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EntityField(BaseModel):
    """Schema for a single extractable entity within a document type."""

    type: str = Field(
        description="Semantic type: monetary, percentage, duration, asset, text, date"
    )
    pattern: str | None = Field(
        default=None,
        description="Optional regex override for extraction",
    )


class AnswerTemplate(BaseModel):
    """Template for rendering a structured answer for a specific query intent."""

    fields: list[str] = Field(default_factory=list)
    verdict_format: str = ""


class DTRConfig(BaseModel):
    """
    Document Type Registry configuration.

    One instance per document type. Passed through every pipeline stage.
    The pipeline code is generic — only this config changes per doc type.
    """

    doc_type: str
    display_name: str = ""

    # ── Extraction ───────────────────────────────────────────────────────────
    entity_schema: dict[str, EntityField] = Field(default_factory=dict)
    """Map of entity_name -> EntityField. Drives entity extraction."""

    # ── Chunking ─────────────────────────────────────────────────────────────
    section_taxonomy: dict[str, list[str]] = Field(default_factory=dict)
    """Map of section_key -> list of heading aliases. Drives section detection."""

    # ── Query handling ───────────────────────────────────────────────────────
    query_intents: list[str] = Field(default_factory=list)
    """Valid query intent types for this document type."""

    risk_patterns: list[str] = Field(default_factory=list)
    """Known risk patterns to flag during analysis."""

    answer_templates: dict[str, AnswerTemplate] = Field(default_factory=dict)
    """Map of intent -> AnswerTemplate for structured answer rendering."""

    # ── Context ──────────────────────────────────────────────────────────────
    regulatory_context: str = ""
    """Regulatory framework injected into LLM prompts."""

    # ── Classification ───────────────────────────────────────────────────────
    classifier_exemplar: str = ""
    """Exemplar text used for embedding-based classification."""

    classifier_terms: list[str] = Field(default_factory=list)
    """Keyword terms for rule-based classification."""

    # ── Helpers ───────────────────────────────────────────────────────────────

    def section_patterns(self) -> dict[str, str]:
        """
        Build regex patterns from section_taxonomy heading aliases.

        Returns a dict like {"coverage": r"\\b(Coverage|Benefit|Sum Insured)\\b"}
        matching the format expected by ChunkerService.
        """
        import re

        patterns: dict[str, str] = {}
        for section_key, aliases in self.section_taxonomy.items():
            if not aliases:
                continue
            escaped = [re.escape(alias) for alias in aliases]
            patterns[section_key] = r"\b(" + "|".join(escaped) + r")\b"
        return patterns

    def intent_labels(self) -> str:
        """Comma-separated intent list for LLM prompts."""
        return ", ".join(self.query_intents)

    @classmethod
    def from_db_row(cls, row: dict) -> DTRConfig:
        """Construct from a database / API response dict (snake_case keys)."""
        entity_schema = {}
        raw_schema = row.get("entity_schema") or row.get("entitySchema") or {}
        for name, field_data in raw_schema.items():
            if isinstance(field_data, dict):
                entity_schema[name] = EntityField(**field_data)
            else:
                entity_schema[name] = EntityField(type=str(field_data))

        answer_templates = {}
        raw_templates = row.get("answer_templates") or row.get("answerTemplates") or {}
        for intent, tmpl_data in raw_templates.items():
            if isinstance(tmpl_data, dict):
                answer_templates[intent] = AnswerTemplate(**tmpl_data)

        return cls(
            doc_type=row.get("doc_type") or row.get("docType", "unknown"),
            display_name=row.get("display_name") or row.get("displayName", ""),
            entity_schema=entity_schema,
            section_taxonomy=row.get("section_taxonomy") or row.get("sectionTaxonomy") or {},
            query_intents=row.get("query_intents") or row.get("queryIntents") or [],
            risk_patterns=row.get("risk_patterns") or row.get("riskPatterns") or [],
            answer_templates=answer_templates,
            regulatory_context=row.get("regulatory_context") or row.get("regulatoryContext") or "",
            classifier_exemplar=row.get("classifier_exemplar") or row.get("classifierExemplar") or "",
            classifier_terms=row.get("classifier_terms") or row.get("classifierTerms") or [],
        )
