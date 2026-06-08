"""DTR Registry — the single source of truth for document type configs at runtime.

Loads configs from the backend API, caches in Redis with TTL, and falls back
to hardcoded seed configs when neither API nor cache is available.
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Optional

from config import get_settings
from dtr.models import DTRConfig
from dtr.seed_configs import SEED_CONFIGS
from utils.logging import get_logger

log = get_logger("dtr.registry")

_REDIS_PREFIX = "dtr:config:"
_REDIS_ALL_KEY = "dtr:configs:all"


class DTRRegistry:
    """Thread-safe singleton registry for DTR configs.

    Loading priority:
      1. Redis cache (fast, TTL-based)
      2. Backend API (authoritative, from PostgreSQL)
      3. Hardcoded seed configs (always available)
    """

    _instance: Optional["DTRRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "DTRRegistry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._configs: dict[str, DTRConfig] = {}
                cls._instance._loaded = False
        return cls._instance

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, doc_type: str) -> DTRConfig:
        """Get DTR config for a doc type, loading from cache/API/seed as needed."""
        if doc_type in self._configs:
            return self._configs[doc_type]

        # Try Redis
        config = self._get_from_redis(doc_type)
        if config:
            self._configs[doc_type] = config
            return config

        # Try seed fallback
        if doc_type in SEED_CONFIGS:
            self._configs[doc_type] = SEED_CONFIGS[doc_type]
            return SEED_CONFIGS[doc_type]

        # Return a minimal default if doc type is completely unknown
        log.warning("dtr.unknown_doc_type", doc_type=doc_type)
        return DTRConfig(doc_type=doc_type, display_name=doc_type.replace("_", " ").title())

    def get_all(self) -> list[DTRConfig]:
        """Return all known configs (cached + seeds)."""
        if self._configs:
            return list(self._configs.values())
        return list(SEED_CONFIGS.values())

    async def load_all(self) -> None:
        """Load all DTR configs from the backend API and cache in Redis."""
        from dtr.loader import fetch_all_dtr_configs

        configs = await fetch_all_dtr_configs()
        if configs:
            for config in configs:
                self._configs[config.doc_type] = config
                self._set_redis(config)
            self._loaded = True
            log.info("dtr.registry_loaded", count=len(configs), source="api")
        else:
            # Fallback to seeds
            self._configs = dict(SEED_CONFIGS)
            self._loaded = True
            log.info("dtr.registry_loaded", count=len(self._configs), source="seed_fallback")

    def invalidate(self, doc_type: str) -> None:
        """Invalidate cache for a specific doc type."""
        self._configs.pop(doc_type, None)
        self._delete_redis(doc_type)
        log.info("dtr.cache_invalidated", doc_type=doc_type)

    def invalidate_all(self) -> None:
        """Invalidate all cached configs."""
        self._configs.clear()
        self._loaded = False
        log.info("dtr.cache_invalidated_all")

    # ── Redis helpers ─────────────────────────────────────────────────────────

    def _get_redis_client(self):
        """Get a sync Redis client (lazy, non-fatal)."""
        try:
            import redis
            import os

            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            return redis.Redis(host=host, port=port, decode_responses=True, socket_timeout=2)
        except Exception:
            return None

    def _get_from_redis(self, doc_type: str) -> Optional[DTRConfig]:
        """Try to load a config from Redis cache."""
        client = self._get_redis_client()
        if not client:
            return None
        try:
            raw = client.get(f"{_REDIS_PREFIX}{doc_type}")
            if raw:
                return DTRConfig.from_db_row(json.loads(raw))
        except Exception as exc:
            log.debug("dtr.redis_get_failed", doc_type=doc_type, error=str(exc))
        return None

    def _set_redis(self, config: DTRConfig) -> None:
        """Cache a config in Redis with TTL."""
        client = self._get_redis_client()
        if not client:
            return
        try:
            settings = get_settings()
            ttl = getattr(settings, "dtr_cache_ttl_seconds", 3600)
            data = config.model_dump(mode="json")
            client.setex(f"{_REDIS_PREFIX}{config.doc_type}", ttl, json.dumps(data))
        except Exception as exc:
            log.debug("dtr.redis_set_failed", doc_type=config.doc_type, error=str(exc))

    def _delete_redis(self, doc_type: str) -> None:
        """Remove a config from Redis cache."""
        client = self._get_redis_client()
        if not client:
            return
        try:
            client.delete(f"{_REDIS_PREFIX}{doc_type}")
        except Exception:
            pass


# ── Module-level convenience ──────────────────────────────────────────────────

def get_registry() -> DTRRegistry:
    """Return the singleton DTR registry instance."""
    return DTRRegistry()
