import httpx

from config import get_settings
from models.schemas import InternalIngestPayload
from utils.logging import get_logger

log = get_logger("services.backend_callback")


class BackendCallback:
    def __init__(self):
        self.settings = get_settings()

    async def ingest(self, document_id: str, payload: InternalIngestPayload) -> None:
        url = f"{self.settings.backend_base_url.rstrip('/')}/internal/documents/{document_id}/ingest"
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                url,
                headers={"X-Internal-Token": self.settings.internal_token},
                json=payload.model_dump(),
            )
            if response.status_code >= 400:
                body = response.text[:500]
                log.error(
                    "callback.ingest_failed",
                    document_id=document_id,
                    url=url,
                    status=response.status_code,
                    body=body,
                )
                raise RuntimeError(
                    f"HTTP {response.status_code} from {url}: {body}"
                )

    async def failed(self, document_id: str, message: str) -> None:
        url = f"{self.settings.backend_base_url.rstrip('/')}/internal/documents/{document_id}/failed"
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                url,
                headers={"X-Internal-Token": self.settings.internal_token},
                json={"message": message},
            )
            if response.status_code >= 400:
                body = response.text[:500]
                log.error(
                    "callback.failed_failed",
                    document_id=document_id,
                    url=url,
                    status=response.status_code,
                    body=body,
                )
                raise RuntimeError(
                    f"HTTP {response.status_code} from {url}: {body}"
                )

