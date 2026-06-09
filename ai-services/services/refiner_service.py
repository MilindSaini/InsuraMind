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
        important_chunks = []
        for chunk in chunks:
            if chunk.sectionType == "noise":
                continue
            if chunk.sectionType in important_sections or chunk.riskLevel == "high" or chunk.importance == "critical":
                important_chunks.append(chunk)

        if not important_chunks:
            return chunks

        batch_size = self.settings.gemini_batch_size
        tasks = []
        for i in range(0, len(important_chunks), batch_size):
            batch = important_chunks[i:i + batch_size]
            tasks.append(self._refine_batch(batch))

        # Execute concurrently
        refined_batches = await asyncio.gather(*tasks, return_exceptions=True)

        refined_map = {}
        failed_batches = 0
        
        for res in refined_batches:
            if isinstance(res, list):
                for chunk in res:
                    refined_map[chunk.chunkIndex] = chunk
            else:
                failed_batches += 1
                log.warning("refiner.batch_failed", error=str(res))

        # Failure threshold protection: if > 50% batches fail, log a severe warning
        if failed_batches > 0 and failed_batches >= len(tasks) / 2:
            log.error("refiner.high_failure_rate", failed=failed_batches, total=len(tasks))

        for i, chunk in enumerate(chunks):
            if chunk.chunkIndex in refined_map:
                chunks[i] = refined_map[chunk.chunkIndex]

        return chunks

    async def _refine_batch(self, batch: list[Chunk]) -> list[Chunk]:
        from google.genai import types
        from pydantic import BaseModel
        import json
        import copy

        class RefinedItem(BaseModel):
            chunkIndex: int
            summary: str

        class RefinedBatchResult(BaseModel):
            items: list[RefinedItem]

        clauses_text = ""
        for chunk in batch:
            clauses_text += f"ID: {chunk.chunkIndex}\nHeading: {chunk.heading}\nText: {chunk.text}\n\n"

        prompt = (
            f"You are a professional document analyst. Review the following clauses extracted from a document.\n\n"
            f"{clauses_text}"
            f"Task:\n"
            f"1. For each clause, refine the text into a clear, concise, and grammatically correct summary sentence.\n"
            f"2. Ensure the information is complete and unambiguous. Do NOT add new information.\n"
            f"3. Return the results matching the provided JSON schema, using the exact ID as 'chunkIndex'.\n"
        )

        try:
            message = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.settings.gemini_fast_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1024,
                    response_mime_type="application/json",
                    response_schema=RefinedBatchResult,
                ),
            )
            text = getattr(message, "text", None) or ""
            if not text:
                return batch
            
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            data = json.loads(text)
            items = data.get("items", [])
            summary_map = {item.get("chunkIndex"): item.get("summary") for item in items if isinstance(item, dict)}
            
            new_batch = []
            for chunk in batch:
                summary = summary_map.get(chunk.chunkIndex)
                if summary:
                    new_chunk = copy.deepcopy(chunk)
                    new_chunk.text = summary.strip()
                    new_batch.append(new_chunk)
                else:
                    new_batch.append(chunk)
            return new_batch
        except Exception as exc:
            log.warning("refiner.batch_process_failed", error=str(exc))
            return batch
