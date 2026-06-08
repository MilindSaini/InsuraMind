from google import genai
import os
import json
from models.schemas import Chunk

class RiskTaggerService:
    """Uses Gemini to assign risk scores and levels to Chunks."""
    def __init__(self):
        self._client = None
        
    def _get_client(self):
        if not self._client:
            self._client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
        return self._client

    async def tag(self, chunks: list[Chunk]) -> list[Chunk]:
        import asyncio
        tasks = []
        for chunk in chunks:
            tasks.append(self._tag_chunk(chunk))
            
        results = await asyncio.gather(*tasks)
        return results

    async def _tag_chunk(self, chunk: Chunk) -> Chunk:
        import asyncio
        prompt = f"""
        You are a risk analysis AI.
        Evaluate the risk level of the following document clause.
        
        Section Type: {chunk.sectionType}
        Heading: {chunk.heading}
        Text: {chunk.text}
        
        Respond with ONLY a JSON object:
        - "risk_score": (float) 0.0 to 10.0 (10 being highest risk)
        - "risk_level": (string) "low", "medium", "high"
        - "risk_reason": (string) Short explanation of why
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
            chunk.riskScore = float(data.get("risk_score", 0.0))
            chunk.riskLevel = str(data.get("risk_level", "low")).lower()
            chunk.riskReason = data.get("risk_reason", "")
            if chunk.riskLevel == "high":
                chunk.importance = "critical"
        except Exception:
            chunk.riskScore = 0.0
            chunk.riskLevel = "low"
            chunk.riskReason = ""
            
        return chunk
