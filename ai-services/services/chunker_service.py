import re
from typing import Any

from models.schemas import Chunk
from utils.text_utils import clean_text, is_noise_text, strip_repeated_headers


class ChunkerService:
    SECTION_PATTERNS = [
        ("waiting_period", r"\b(waiting period|pre-existing|ped|survival period)\b"),
        ("exclusion", r"\b(exclusion|not covered|excluded|limitations|permanent exclusion)\b"),
        ("coverage", r"\b(coverage|benefit|covered|sum insured|room rent|cashless)\b"),
        ("claim_rule", r"\b(claim|documents required|intimation|settlement|deductible|co-pay|copay)\b"),
        ("definition", r"\b(definition|means|interpretation)\b"),
        ("renewal", r"\b(renewal|cancellation|termination|grace period)\b"),
    ]

    def chunk(self, pages: list[dict[str, Any]]) -> list[Chunk]:
        raw_sections: list[tuple[str | None, str, int]] = []
        for page in pages:
            page_no = int(page.get("page", 1))
            text = clean_text(page.get("text", ""))
            if not text:
                continue
            raw_sections.extend(self._split_page(text, page_no))

        chunks: list[Chunk] = []
        for heading, text, page_no in raw_sections:
            # Strip repeated watermark/header lines before processing
            text = strip_repeated_headers(text)
            if not text.strip():
                continue
            for part in self._fit_size(text, 1800):
                # Check noise BEFORE section classification — prevents
                # watermark text with keywords from polluting insight cards
                if is_noise_text(part):
                    section_type = "noise"
                else:
                    section_type = self._section_type(f"{heading or ''}\n{part}")
                risk_level = self._risk(section_type, part)
                chunk = Chunk(
                    chunkIndex=len(chunks),
                    sectionType=section_type,
                    heading=heading,
                    parentHeading=heading,
                    text=part,
                    pageNumber=page_no,
                    riskLevel=risk_level,
                    importance="low" if section_type == "noise" else ("critical" if risk_level == "high" else "normal"),
                    citationLabel=f"p.{page_no} c.{len(chunks) + 1}",
                )
                chunks.append(chunk)
        return chunks

    def _split_page(self, text: str, page_no: int) -> list[tuple[str | None, str, int]]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return []

        sections: list[tuple[str | None, list[str]]] = []
        current_heading: str | None = None
        current: list[str] = []

        for line in lines:
            if self._looks_like_heading(line):
                if current:
                    sections.append((current_heading, current))
                    current = []
                current_heading = line[:180]
            else:
                current.append(line)

        if current:
            sections.append((current_heading, current))

        if not sections:
            sections.append((None, lines))
        return [(heading, clean_text("\n".join(content)), page_no) for heading, content in sections if content]

    def _looks_like_heading(self, line: str) -> bool:
        if len(line) > 140:
            return False
        if re.match(r"^(\d+(\.\d+)*|[A-Z])[\). -]+[A-Za-z]", line):
            return True
        keywordish = any(re.search(pattern, line, re.I) for _, pattern in self.SECTION_PATTERNS)
        upperish = sum(1 for ch in line if ch.isupper()) >= max(4, len(line.replace(" ", "")) // 2)
        return keywordish and upperish

    def _fit_size(self, text: str, max_chars: int) -> list[str]:
        if len(text) <= max_chars:
            return [text]
        sentences = re.split(r"(?<=[.!?])\s+", text)
        parts: list[str] = []
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) > max_chars and current:
                parts.append(clean_text(current))
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            parts.append(clean_text(current))
        return parts

    def _section_type(self, text: str) -> str:
        for section_type, pattern in self.SECTION_PATTERNS:
            if re.search(pattern, text, re.I):
                return section_type
        return "general"

    def _risk(self, section_type: str, text: str) -> str:
        t = text.lower()
        if section_type == "noise":
            return "low"
        if section_type in {"exclusion", "waiting_period"}:
            return "high"
        if any(term in t for term in ["co-pay", "copay", "deductible", "sub-limit", "room rent", "not payable"]):
            return "medium"
        return "low"
