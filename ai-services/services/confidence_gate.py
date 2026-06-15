"""Confidence gate — decides whether to skip LLM for a section.

Before calling Gemini, ask:
  1. Is this clause already extracted confidently by regex/spaCy?
  2. Do we already have the expected entities from regex/spaCy?
  3. Is the section type simple enough to skip LLM?

If yes → skip LLM and save cost.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from utils.logging import get_logger

if TYPE_CHECKING:
    from dtr.models import DTRConfig

log = get_logger("services.confidence_gate")

# Section types that are inherently simple and rarely need LLM enrichment
_SIMPLE_SECTIONS = frozenset({"definition", "general", "noise", "authority", "validity"})


def should_skip_llm(
    clauses: list[dict],
    entities: list[dict],
    section_type: str,
    dtr_config: Optional["DTRConfig"],
    threshold: float = 0.7,
) -> bool:
    """Decide whether LLM extraction can be skipped for this section.

    Returns True if the rule-based + spaCy extraction is confident enough.
    """
    # 1. Simple sections — always skip LLM
    if section_type in _SIMPLE_SECTIONS:
        log.info("confidence_gate.skip_simple", section_type=section_type)
        return True

    # 2. No clauses extracted at all — must call LLM to get something
    if not clauses:
        return False

    # 3. Assess overall extraction confidence
    confidence = assess_extraction_confidence(clauses, entities, dtr_config)

    skip = confidence >= threshold
    log.info(
        "confidence_gate.decision",
        section_type=section_type,
        confidence=round(confidence, 3),
        threshold=threshold,
        skip_llm=skip,
        clause_count=len(clauses),
        entity_count=len(entities),
    )
    return skip


def assess_extraction_confidence(
    clauses: list[dict],
    entities: list[dict],
    dtr_config: Optional["DTRConfig"],
) -> float:
    """Compute weighted extraction confidence for a section.

    Factors:
      - Average clause confidence from regex/spaCy (weight: 0.4)
      - Entity coverage ratio vs DTR entity_schema (weight: 0.35)
      - Clause count heuristic — more clauses = more confident (weight: 0.25)

    Returns 0.0–1.0.
    """
    if not clauses:
        return 0.0

    # Factor 1: Average clause confidence
    clause_confidences = [c.get("confidence", 0.0) for c in clauses]
    avg_clause_conf = sum(clause_confidences) / len(clause_confidences)

    # Factor 2: Entity coverage ratio
    entity_coverage = _entity_coverage_ratio(entities, dtr_config)

    # Factor 3: Clause count heuristic (more clauses = more complete extraction)
    # Caps at 1.0 for 3+ clauses
    clause_count_score = min(len(clauses) / 3.0, 1.0)

    # Weighted combination
    confidence = (
        avg_clause_conf * 0.4
        + entity_coverage * 0.35
        + clause_count_score * 0.25
    )
    return min(confidence, 1.0)


def _entity_coverage_ratio(
    entities: list[dict],
    dtr_config: Optional["DTRConfig"],
) -> float:
    """What fraction of expected entity types have been extracted?"""
    if not dtr_config or not dtr_config.entity_schema:
        # No DTR config — can't assess coverage, assume moderate
        return 0.5

    expected_types = set(dtr_config.entity_schema.keys())
    if not expected_types:
        return 0.5

    found_types = {e.get("entityType") or e.get("entity_type", "") for e in entities}
    covered = expected_types & found_types
    return len(covered) / len(expected_types)
