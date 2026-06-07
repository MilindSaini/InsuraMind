import re
from typing import Iterable


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+", text.lower())


def unique_word_ratio(text: str) -> float:
    tokens = words(text)
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def text_to_unique_word_ratio(text: str) -> float:
    tokens = words(text)
    if not tokens:
        return 0.0
    return len(tokens) / max(1, len(set(tokens)))


def is_noise_text(text: str, *, ratio_threshold: float = 2.2, min_words: int = 12) -> bool:
    tokens = words(text)
    if len(tokens) < min_words:
        return False
    if text_to_unique_word_ratio(text) >= ratio_threshold:
        return True
    return is_header_noise(text)


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


def strip_repeated_headers(text: str, *, max_repeats: int = 2) -> str:
    """Remove lines that appear more than `max_repeats` times (watermarks, headers)."""
    lines = text.splitlines()
    counts: dict[str, int] = {}
    for line in lines:
        key = line.strip().lower()
        if key:
            counts[key] = counts.get(key, 0) + 1
    cleaned = [line for line in lines if not line.strip() or counts.get(line.strip().lower(), 0) <= max_repeats]
    return "\n".join(cleaned).strip()


def is_header_noise(text: str) -> bool:
    """Detect chunks dominated by company names / watermarks."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    counts: dict[str, int] = {}
    for line in lines:
        key = line.lower()
        counts[key] = counts.get(key, 0) + 1
    most_common_count = max(counts.values())
    return most_common_count >= 3 and most_common_count / len(lines) >= 0.4


def first_non_empty(values: Iterable[str | None], fallback: str = "") -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return fallback
