from google import genai
import os
import json
from typing import Optional
from dtr.models import DTRConfig

class ClauseExtractorService:
    """Uses Gemini to extract structured clauses from sections."""
    def __init__(self):
        self._client = None
        
    def _get_client(self):
        if not self._client:
            self._client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
        return self._client

    async def extract(self, sections: list[dict], config: Optional[DTRConfig] = None) -> list[dict]:
        import asyncio
        clauses = []
        tasks = []
        for sec in sections:
            if sec["section_type"] == "noise":
                continue
            tasks.append(self._extract_clauses(sec, config))
            
        results = await asyncio.gather(*tasks)
        for r in results:
            clauses.extend(r)
        return clauses

    async def _extract_clauses(self, section: dict, config: Optional[DTRConfig]) -> list[dict]:
        import asyncio
        prompt = f"""
        You are an expert document extraction AI.
        Extract specific clauses from the provided text.
        A clause represents a specific rule, benefit, limit, or condition.
        
        Section Type: {section['section_type']}
        Text:
        {section['text']}
        
        Respond with ONLY a JSON array of objects, where each object has:
        - "type": (string) e.g., "WAITING_PERIOD", "COVERAGE", "EXCLUSION" (try to use the section type if applicable)
        - "title": (string) A short 2-4 word title for the clause
        - "value": (string) The value, amount, or concise summary
        
        If no meaningful clauses exist in this text, return an empty array [].
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
            if isinstance(data, list):
                for item in data:
                    item["source_section"] = section
                return data
            return []
        except Exception:
            return []
