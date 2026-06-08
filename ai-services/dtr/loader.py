"""DTR Loader — fetches DTR configs from the Spring Boot backend internal API."""

from __future__ import annotations

import json
from typing import Optional

import httpx

from config import get_settings
from dtr.models import DTRConfig
from utils.logging import get_logger

log = get_logger("dtr.loader")


async def fetch_all_dtr_configs() -> list[DTRConfig]:
    """Fetch all enabled DTR configs from the backend internal API."""
    settings = get_settings()
    url = f"{settings.backend_base_url.rstrip('/')}/internal/dtr"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                url,
                headers={"X-Internal-Token": settings.internal_token},
            )
            if response.status_code >= 400:
                log.warning(
                    "dtr.fetch_all_failed",
                    status=response.status_code,
                    body=response.text[:300],
                )
                return []
            rows = response.json()
            configs = [DTRConfig.from_db_row(row) for row in rows]
            log.info("dtr.fetch_all_ok", count=len(configs))
            return configs
    except Exception as exc:
        log.warning("dtr.fetch_all_error", error=str(exc))
        return []


async def fetch_dtr_config(doc_type: str) -> Optional[DTRConfig]:
    """Fetch a single DTR config by doc_type from the backend internal API."""
    settings = get_settings()
    url = f"{settings.backend_base_url.rstrip('/')}/internal/dtr/{doc_type}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                url,
                headers={"X-Internal-Token": settings.internal_token},
            )
            if response.status_code == 404:
                return None
            if response.status_code >= 400:
                log.warning(
                    "dtr.fetch_one_failed",
                    doc_type=doc_type,
                    status=response.status_code,
                )
                return None
            return DTRConfig.from_db_row(response.json())
    except Exception as exc:
        log.warning("dtr.fetch_one_error", doc_type=doc_type, error=str(exc))
        return None
