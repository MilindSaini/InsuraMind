import httpx

from config import get_settings


class BackendContextClient:
    def __init__(self):
        self.settings = get_settings()

    async def fetch_chunks(self, document_id: str) -> list[dict]:
        url = f"{self.settings.backend_base_url.rstrip('/')}/internal/documents/{document_id}/chunks"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url,
                headers={"X-Internal-Token": self.settings.internal_token},
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []