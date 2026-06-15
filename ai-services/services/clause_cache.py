"""Clause extraction cache — Redis-backed, keyed by content hash.

Cache key = sha256(section_text + doc_type + extractor_version)

When the same clause text appears in another document (or a re-uploaded
version), we return the cached extraction instantly — zero LLM cost.

Bumping EXTRACTOR_VERSION in config invalidates all caches automatically
because the hash changes.
"""

from __future__ import annotations

import hashlib
import json
from typing import Optional

from config import get_settings
from utils.logging import get_logger

log = get_logger("services.clause_cache")

_CACHE_PREFIX = "CLAUSE_CACHE:"


def compute_clause_hash(section_text: str, doc_type: str, extractor_version: str) -> str:
    """Deterministic hash for a section's extraction result."""
    payload = f"{section_text}|{doc_type}|{extractor_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ClauseCache:
    """Redis-backed clause extraction cache.

    Falls back to no-op if Redis is unavailable — the pipeline simply
    re-extracts without caching.
    """

    def __init__(self):
        self._redis = None
        self.settings = get_settings()

    async def _get_redis(self):
        """Lazy Redis connection (shares the same Redis as the pipeline worker)."""
        if self._redis is not None:
            return self._redis
        try:
            import os
            import redis.asyncio as aioredis

            host = os.getenv("REDIS_HOST", "localhost")
            port = os.getenv("REDIS_PORT", "6379")
            url = os.getenv("REDIS_URL", f"redis://{host}:{port}")
            self._redis = aioredis.from_url(url, decode_responses=True)
            await self._redis.ping()
            return self._redis
        except Exception as exc:
            log.warning("clause_cache.redis_unavailable", error=str(exc))
            self._redis = None
            return None

    async def get_cached(self, clause_hash: str) -> Optional[list[dict]]:
        """Look up cached extraction result by hash.

        Returns a list of clause dicts if cached, None if miss.
        """
        r = await self._get_redis()
        if r is None:
            return None
        try:
            key = f"{_CACHE_PREFIX}{clause_hash}"
            raw = await r.get(key)
            if raw is None:
                return None
            data = json.loads(raw)
            log.info("clause_cache.hit", hash=clause_hash[:12])
            return data
        except Exception as exc:
            log.warning("clause_cache.get_failed", error=str(exc))
            return None

    async def put_cached(self, clause_hash: str, clauses: list[dict]) -> None:
        """Store extraction result with TTL."""
        r = await self._get_redis()
        if r is None:
            return
        try:
            key = f"{_CACHE_PREFIX}{clause_hash}"
            payload = json.dumps(clauses, default=str)
            await r.setex(key, self.settings.clause_cache_ttl_seconds, payload)
            log.info("clause_cache.stored", hash=clause_hash[:12], clauses=len(clauses))
        except Exception as exc:
            log.warning("clause_cache.put_failed", error=str(exc))

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None
