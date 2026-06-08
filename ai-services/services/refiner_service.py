"""Insight refiner — Uses Gemini to rewrite raw OCR chunks into clean insights."""

import asyncio
from typing import Optional

from config import get_settings
from dtr.models import DTRConfig
from models.schemas import Chunk
from utils.logging import get_logger

log = get_logger("services.refiner")


class RefinerService:
    def __init__(self):
        self.settings = get_settings()
        self.client = self._client()

    def _client(self):
        if not self.settings.gemini_api_key:
            return None
        try:
            from google import genai
            return genai.Client(api_key=self.settings.gemini_api_key)
        except Exception as exc:
            log.warning("refiner.gemini_init_failed", error=str(exc))
            return None

    async def refine(
        self, chunks: list[Chunk], config: Optional[DTRConfig] = None
    ) -> list[Chunk]:
        if not self.client:
            log.warning("refiner.skipped", reason="No Gemini client available")
            return chunks

        important_sections = {"coverage", "exclusion", "waiting_period", "claim_rule"}
        if config and config.section_taxonomy:
            important_sections.update(config.section_taxonomy.keys())

        # Filter chunks that need refinement
        tasks = []
        for chunk in chunks:
            if chunk.sectionType == "noise":
                continue
            if chunk.sectionType in important_sections or chunk.riskLevel == "high" or chunk.importance == "critical":
                tasks.append(self._refine_chunk(chunk))

        if not tasks:
            return chunks

        # Execute concurrently
        refined_chunks = await asyncio.gather(*tasks, return_exceptions=True)

        # Apply successful refinements
        refined_map = {}
        for res in refined_chunks:
            if isinstance(res, Chunk):
                refined_map[res.chunkIndex] = res

        for i, chunk in enumerate(chunks):
            if chunk.chunkIndex in refined_map:
                chunks[i] = refined_map[chunk.chunkIndex]

        return chunks

    async def _refine_chunk(self, chunk: Chunk) -> Chunk:
        from google.genai import types
        from pydantic import BaseModel
        import json
        import copy

        class RefinedResult(BaseModel):
            summary: str

        prompt = (
            f"You are a professional document analyst. Review the following clause extracted from a document.\n\n"
            f"Clause Heading: {chunk.heading}\n"
            f"Clause Value/Text: {chunk.text}\n\n"
            f"Task:\n"
            f"1. Refine the clause value into a clear, concise, and grammatically correct summary sentence.\n"
            f"2. Ensure the information is complete and unambiguous.\n"
            f"3. Do NOT add new information that is not in the text.\n\n"
            f"Return ONLY a JSON object with a 'summary' key containing the refined text."
        )

        try:
            # We must use asyncio.to_thread because client.models.generate_content is synchronous
            message = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.settings.gemini_fast_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=300,
                    response_mime_type="application/json",
                    response_schema=RefinedResult,
                ),
            )
            text = getattr(message, "text", None) or ""
            if not text:
                return chunk
            
            # Clean up potential markdown formatting
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            data = json.loads(text)
            new_chunk = copy.deepcopy(chunk)
            if data.get("summary"):
                new_chunk.text = data["summary"].strip()
            return new_chunk
        except Exception as exc:
            log.warning("refiner.chunk_failed", chunk_index=chunk.chunkIndex, error=str(exc))
            return chunk
