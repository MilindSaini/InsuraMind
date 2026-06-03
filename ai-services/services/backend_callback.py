import httpx

from config import get_settings
from models.schemas import InternalIngestPayload


class BackendCallback:
    def __init__(self):
        self.settings = get_settings()

    async def ingest(self, document_id: str, payload: InternalIngestPayload) -> None:
        url = f"{self.settings.backend_base_url.rstrip('/')}/internal/documents/{document_id}/ingest"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={"X-Internal-Token": self.settings.internal_token},
                json=payload.model_dump(),
            )
            response.raise_for_status()

    async def failed(self, document_id: str, message: str) -> None:
        url = f"{self.settings.backend_base_url.rstrip('/')}/internal/documents/{document_id}/failed"
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                url,
                headers={"X-Internal-Token": self.settings.internal_token},
                json={"message": message},
            )
            response.raise_for_status()
