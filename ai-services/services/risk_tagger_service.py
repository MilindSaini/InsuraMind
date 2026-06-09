from google import genai
from google.genai import types
from pydantic import BaseModel
import os
import json
from config import get_settings

class RiskTaggerService:
    """Uses Gemini to assign risk scores and levels to clauses."""
    def __init__(self):
        self._client = None
        self.settings = get_settings()
        
    def _get_client(self):
        if not self._client:
            api_key = self.settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
            self._client = genai.Client(api_key=api_key) if api_key else None
        return self._client

    async def tag(self, clauses: list[dict]) -> list[dict]:
        import asyncio
        if not self._get_client():
            return clauses

        batch_size = self.settings.gemini_batch_size
        tasks = []
        
        # Enumerate clauses so we can map results back by index
        indexed_clauses = list(enumerate(clauses))
        
        for i in range(0, len(indexed_clauses), batch_size):
            batch = indexed_clauses[i:i + batch_size]
            tasks.append(self._tag_batch(batch))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge results
        for res in results:
            if isinstance(res, list):
                for idx, tags in res:
                    clauses[idx].update(tags)
                    
        return clauses

    async def _tag_batch(self, indexed_batch: list[tuple[int, dict]]) -> list[tuple[int, dict]]:
        import asyncio
        
        class RiskTag(BaseModel):
            index: int
            risk_score: float
            risk_level: str
            risk_reason: str

        class RiskBatchResult(BaseModel):
            items: list[RiskTag]

        clauses_text = ""
        for idx, clause in indexed_batch:
            sec = clause.get("source_section", {})
            section_type = sec.get("section_type", "general")
            heading = clause.get("title", sec.get("heading", ""))
            text = clause.get("value", "")
            clauses_text += f"Index: {idx}\nSection Type: {section_type}\nHeading: {heading}\nText: {text}\n\n"

        prompt = f"""
        You are a risk analysis AI.
        Evaluate the risk level of the following document clauses.
        
        {clauses_text}
        
        Task:
        For each clause, provide a risk score (0.0 to 10.0, 10 being highest risk), 
        a risk level ("low", "medium", "high"), and a short explanation (risk_reason).
        Return the results matching the provided JSON schema, using the exact Index as 'index'.
        """
        
        client = self._get_client()
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.settings.gemini_fast_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RiskBatchResult
                )
            )
            text = getattr(response, "text", None) or ""
            if not text:
                return []
                
            text = text.strip()
            if text.startswith("```json"): text = text[7:]
            elif text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            text = text.strip()
            
            data = json.loads(text)
            items = data.get("items", [])
            
            batch_updates = []
            for item in items:
                idx = item.get("index")
                if idx is not None:
                    tags = {
                        "risk_score": float(item.get("risk_score", 0.0)),
                        "risk_level": str(item.get("risk_level", "low")).lower(),
                        "risk_reason": str(item.get("risk_reason", ""))
                    }
                    batch_updates.append((idx, tags))
            return batch_updates
        except Exception:
            return []
