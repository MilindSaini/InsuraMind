import re
from typing import Iterable


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+", text.lower())


def keyword_score(query: str, text: str) -> float:
    q = set(words(query))
    if not q:
        return 0.0
    t = set(words(text))
    return len(q & t) / max(1, len(q))


def section_hint(query: str) -> str | None:
    q = query.lower()
    topic_map = [
        ("waiting_period", ["waiting period", "waiting", "pre-existing", "ped", "survival period"]),
        ("exclusion", ["exclusion", "excluded", "exclusions", "not covered", "limitations"]),
        ("coverage", ["coverage", "covered", "benefit", "benefits", "summarize", "summary"]),
        ("claim_rule", ["claim", "claims", "rejection", "reject", "reject my claim", "intimation"]),
        ("definition", ["define", "definition", "means", "meaning"]),
        ("renewal", ["renewal", "cancel", "cancellation", "termination", "grace period"]),
    ]
    for section, terms in topic_map:
        if any(term in q for term in terms):
            return section
    return None


def topic_label(section_type: str | None) -> str:
    return {
        "waiting_period": "waiting period",
        "exclusion": "exclusions",
        "coverage": "coverage",
        "claim_rule": "claim rules",
        "definition": "definitions",
        "renewal": "renewal rules",
    }.get(section_type or "", "this topic")


def first_non_empty(values: Iterable[str | None], fallback: str = "") -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return fallback
