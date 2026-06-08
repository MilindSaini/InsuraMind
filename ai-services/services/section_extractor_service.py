from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from google import genai
import os
import json
from typing import Optional
from dtr.models import DTRConfig

class SectionExtractorService:
    """Uses Docling HybridChunker and Gemini to group document blocks into semantic sections."""
    def __init__(self):
        self._chunker = HybridChunker()
        self._client = None
        
    def _get_client(self):
        if not self._client:
            self._client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
        return self._client

    async def extract(self, docling_doc, config: Optional[DTRConfig] = None) -> list[dict]:
        import asyncio
        chunk_iter = self._chunker.chunk(docling_doc)
        raw_chunks = list(chunk_iter)
        
        sections = []
        tasks = []
        for i, chunk in enumerate(raw_chunks):
            tasks.append(self._classify_section(chunk, i, config))
            
        results = await asyncio.gather(*tasks)
        for r in results:
            if r:
                sections.append(r)
        return sections

    async def _classify_section(self, chunk, index: int, config: Optional[DTRConfig]) -> dict:
        import asyncio
        allowed_sections = list(config.section_taxonomy.keys()) if config and config.section_taxonomy else ["coverage", "exclusion", "waiting_period", "claim_rule", "definition", "renewal", "general"]
        
        prompt = f"""
        Analyze the following document text block and classify it into exactly one of the following section types:
        {allowed_sections}
        
        If it doesn't clearly match any, use 'general'.
        If it contains generic noise or watermarks, use 'noise'.
        
        Text Block:
        {chunk.text}
        
        Respond with ONLY a JSON object: {{"section": "selected_type"}}
        """
        
        client = self._get_client()
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            data = json.loads(response.text)
            section_type = data.get("section", "general")
        except Exception:
            section_type = "general"
            
        # Safely extract page number and heading
        page_no = 1
        heading = None
        if chunk.meta:
            if chunk.meta.doc_items and len(chunk.meta.doc_items) > 0:
                item = chunk.meta.doc_items[0]
                if hasattr(item, 'prov') and item.prov and len(item.prov) > 0:
                    page_no = getattr(item.prov[0], 'page_no', 1)
            if chunk.meta.headings and len(chunk.meta.headings) > 0:
                heading = chunk.meta.headings[0]

        return {
            "chunk_index": index,
            "section_type": section_type,
            "text": chunk.text,
            "heading": heading,
            "page_number": page_no
        }
