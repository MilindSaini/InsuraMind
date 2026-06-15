"""Section extractor — uses Docling HybridChunker + rule-first classification.

Rule-first approach:
  1. Try keyword/regex matching against DTR section_taxonomy aliases
  2. Only call Gemini if no confident match found

This alone eliminates N Gemini calls per document (one per chunk) for
standard documents that match DTR patterns.
"""

import re
from typing import Optional

from docling_core.transforms.chunker.hybrid_chunker import HybridChunker

from dtr.models import DTRConfig
from utils.logging import get_logger

log = get_logger("services.section_extractor")


class SectionExtractorService:
    """Uses Docling HybridChunker and rule-first classification to group
    document blocks into semantic sections."""

    def __init__(self):
        self._chunker = HybridChunker()
        self._client = None
        self._compiled_patterns: dict[str, re.Pattern] = {}

    def _get_client(self):
        if not self._client:
            import os
            from google import genai
            api_key = os.environ.get("GEMINI_API_KEY", "")
            if api_key:
                self._client = genai.Client(api_key=api_key)
        return self._client

    async def extract(self, docling_doc, config: Optional[DTRConfig] = None) -> list[dict]:
        import asyncio

        chunk_iter = self._chunker.chunk(docling_doc)
        raw_chunks = list(chunk_iter)

        # Pre-compile taxonomy patterns for fast matching
        taxonomy_patterns = self._compile_taxonomy(config)

        sections = []
        llm_tasks = []

        for i, chunk in enumerate(raw_chunks):
            # ── Step 1: Try rule-based classification ────────────────────
            section_type = self._classify_by_rules(chunk.text, taxonomy_patterns)

            if section_type is not None:
                # Confident rule match — no LLM needed
                section = self._build_section(chunk, i, section_type)
                sections.append((i, section))
                log.info(
                    "section.rule_match",
                    chunk_index=i,
                    section_type=section_type,
                )
            else:
                # ── Step 2: Fall back to LLM classification ──────────────
                llm_tasks.append((i, chunk, config))

        # Run LLM classification for unmatched chunks (in parallel)
        if llm_tasks:
            log.info("section.llm_fallback", count=len(llm_tasks), total=len(raw_chunks))
            import asyncio
            coros = [
                self._classify_section_llm(chunk, idx, cfg)
                for idx, chunk, cfg in llm_tasks
            ]
            results = await asyncio.gather(*coros)
            for (idx, _, _), result in zip(llm_tasks, results):
                if result:
                    sections.append((idx, result))

        # Sort by original chunk index to maintain document order
        sections.sort(key=lambda x: x[0])
        return [s for _, s in sections]

    # ── Rule-based classification ─────────────────────────────────────────────

    def _compile_taxonomy(self, config: Optional[DTRConfig]) -> dict[str, re.Pattern]:
        """Compile DTR section_taxonomy aliases into regex patterns."""
        if not config or not config.section_taxonomy:
            # Fallback: basic insurance patterns
            return {
                "coverage": re.compile(
                    r"\b(coverage|benefit|sum insured|room rent|cashless)\b", re.I
                ),
                "exclusion": re.compile(
                    r"\b(exclusion|not covered|excluded|limitations|permanent exclusion)\b", re.I
                ),
                "waiting_period": re.compile(
                    r"\b(waiting period|pre-existing|ped|survival period)\b", re.I
                ),
                "claim_rule": re.compile(
                    r"\b(claim|documents required|intimation|settlement|deductible|co-?pay)\b", re.I
                ),
                "definition": re.compile(
                    r"\b(definition|means|interpretation)\b", re.I
                ),
                "renewal": re.compile(
                    r"\b(renewal|cancellation|termination|grace period)\b", re.I
                ),
            }

        patterns = {}
        for section_key, aliases in config.section_taxonomy.items():
            if aliases:
                escaped = [re.escape(alias) for alias in aliases]
                patterns[section_key] = re.compile(
                    r"\b(" + "|".join(escaped) + r")\b", re.I
                )
        return patterns

    def _classify_by_rules(
        self,
        text: str,
        taxonomy_patterns: dict[str, re.Pattern],
    ) -> Optional[str]:
        """Classify a chunk by keyword matching against taxonomy patterns.

        Returns section_type if a confident match is found, None otherwise.
        """
        if not text or not taxonomy_patterns:
            return None

        # Check first 500 chars (heading area) with higher weight
        header_text = text[:500]
        full_text = text

        scores: dict[str, int] = {}

        for section_key, pattern in taxonomy_patterns.items():
            # Header matches count double
            header_matches = len(pattern.findall(header_text))
            body_matches = len(pattern.findall(full_text))
            score = header_matches * 2 + body_matches

            if score > 0:
                scores[section_key] = score

        if not scores:
            return None

        # Check for noise (very short, generic text)
        if len(text.strip()) < 30:
            return "noise"

        # Return the best match if it's confident enough
        best_key = max(scores, key=scores.get)
        best_score = scores[best_key]

        # Require at least 2 match points for confidence
        if best_score >= 2:
            return best_key

        # Single match in header is still acceptable
        if best_score >= 1 and header_text:
            return best_key

        return None

    # ── LLM fallback classification ───────────────────────────────────────────

    async def _classify_section_llm(
        self, chunk, index: int, config: Optional[DTRConfig]
    ) -> Optional[dict]:
        """Fall back to Gemini for section classification."""
        import asyncio

        allowed_sections = (
            list(config.section_taxonomy.keys())
            if config and config.section_taxonomy
            else ["coverage", "exclusion", "waiting_period", "claim_rule", "definition", "renewal", "general"]
        )

        prompt = f"""Analyze the following document text block and classify it into exactly one of these section types:
{allowed_sections}

If it doesn't clearly match any, use 'general'.
If it contains generic noise or watermarks, use 'noise'.

Text Block:
{chunk.text}

Respond with ONLY a JSON object: {{"section": "selected_type"}}
"""
        client = self._get_client()
        if not client:
            # No LLM available — default to general
            return self._build_section(chunk, index, "general")

        try:
            import json
            from google.genai import types

            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            data = json.loads(response.text)
            section_type = data.get("section", "general")
        except Exception:
            section_type = "general"

        return self._build_section(chunk, index, section_type)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_section(self, chunk, index: int, section_type: str) -> dict:
        """Build a section dict from a Docling chunk."""
        page_no = 1
        heading = None
        if chunk.meta:
            if chunk.meta.doc_items and len(chunk.meta.doc_items) > 0:
                item = chunk.meta.doc_items[0]
                if hasattr(item, "prov") and item.prov and len(item.prov) > 0:
                    page_no = getattr(item.prov[0], "page_no", 1)
            if chunk.meta.headings and len(chunk.meta.headings) > 0:
                heading = chunk.meta.headings[0]

        return {
            "chunk_index": index,
            "section_type": section_type,
            "text": chunk.text,
            "heading": heading,
            "page_number": page_no,
        }
