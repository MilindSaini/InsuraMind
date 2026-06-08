"""Durable document pipeline worker backed by Redis Streams.

Replaces FastAPI BackgroundTasks with a real at-least-once delivery consumer.

Stream: document.pipeline.jobs   (published by Spring Boot after upload)
Group:  ai-pipeline-workers
Consumer: ai-worker-{hostname}

Retry policy:
  - Up to MAX_RETRIES delivery attempts per message.
  - After MAX_RETRIES failures the message is XACK'd and published to DLQ.

Dead-letter queue: document.pipeline.dlq
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
from typing import Any

from utils.logging import get_logger
from pipeline.context import PipelineContext
from pipeline.stages import PIPELINE_STAGES, StageError

log = get_logger("pipeline.worker")

STREAM_KEY = os.getenv("PIPELINE_STREAM", "document.pipeline.jobs")
DLQ_KEY = os.getenv("PIPELINE_DLQ", "document.pipeline.dlq")
GROUP_NAME = os.getenv("PIPELINE_GROUP", "ai-pipeline-workers")
CONSUMER_NAME = f"ai-worker-{socket.gethostname()}"
MAX_RETRIES = int(os.getenv("PIPELINE_MAX_RETRIES", "3"))
BLOCK_MS = 2000  # Long-poll timeout
BATCH_SIZE = 5   # Messages read per iteration


class DocumentPipelineWorker:
    """Redis Streams consumer that processes document pipeline events."""

    def __init__(self):
        self._redis = None
        self._running = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Connect to Redis and start consuming. Call once on app startup."""
        self._redis = await self._connect_redis()
        if self._redis is None:
            log.warning(
                "worker.redis_unavailable",
                reason="REDIS_URL not set or Redis unreachable — pipeline worker disabled",
            )
            return
        await self._ensure_consumer_group()
        self._running = True
        asyncio.create_task(self._consume_loop(), name="pipeline-worker")
        log.info("worker.started", stream=STREAM_KEY, group=GROUP_NAME, consumer=CONSUMER_NAME)

    async def stop(self) -> None:
        self._running = False
        if self._redis:
            await self._redis.aclose()
        log.info("worker.stopped")

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _consume_loop(self) -> None:
        while self._running:
            try:
                tasks = []
                # 1. Reclaim stale messages from crashed consumers (PEL)
                reclaimed = await self._reclaim_stale()
                for msg_id, data in reclaimed:
                    tasks.append(asyncio.create_task(self._handle_message(msg_id, data)))

                # 2. Read new messages
                results = await self._redis.xreadgroup(
                    groupname=GROUP_NAME,
                    consumername=CONSUMER_NAME,
                    streams={STREAM_KEY: ">"},
                    count=BATCH_SIZE,
                    block=BLOCK_MS,
                )
                if results:
                    for _stream, messages in results:
                        for msg_id, data in messages:
                            tasks.append(asyncio.create_task(self._handle_message(msg_id, data)))
                            
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                if not self._running:
                    break
                log.error("worker.loop_error", error=str(exc), exc_info=True)
                await asyncio.sleep(5)  # Back-off before retry

    # ── Message handling ───────────────────────────────────────────────────────

    async def _handle_message(self, msg_id: bytes, data: dict[bytes, bytes]) -> None:
        raw = {k.decode(): v.decode() for k, v in data.items()}
        document_id = raw.get("documentId", "unknown")

        try:
            event = json.loads(raw.get("payload", "{}"))
        except json.JSONDecodeError:
            event = raw  # Fallback: treat the raw fields as the event

        log.info("worker.message_received", msg_id=msg_id, document_id=document_id)

        try:
            ctx = PipelineContext.from_event(event)
            await self._run_pipeline(ctx)
            await self._redis.xack(STREAM_KEY, GROUP_NAME, msg_id)
            log.info("worker.message_acked", msg_id=msg_id, document_id=document_id)

        except Exception as exc:
            delivery_count = await self._delivery_count(msg_id)
            log.error(
                "worker.message_failed",
                msg_id=msg_id,
                document_id=document_id,
                delivery=delivery_count,
                error=str(exc),
            )
            if delivery_count >= MAX_RETRIES:
                await self._dead_letter(msg_id, raw, str(exc))
                await self._redis.xack(STREAM_KEY, GROUP_NAME, msg_id)
                # Notify backend of failure
                await self._notify_failed(document_id, str(exc))

    # ── Pipeline execution ─────────────────────────────────────────────────────

    async def _run_pipeline(self, ctx: PipelineContext) -> None:
        for StageClass in PIPELINE_STAGES:
            stage = StageClass()
            ctx.start_stage(stage.name)
            try:
                ctx = await stage.execute(ctx)
            except StageError as exc:
                log.error(
                    "stage.failed",
                    stage=exc.stage,
                    document_id=ctx.document_id,
                    reason=exc.reason,
                )
                raise
            finally:
                ctx.finish_stage(stage.name)

    # ── Redis helpers ──────────────────────────────────────────────────────────

    @staticmethod
    async def _connect_redis():
        redis_url = os.getenv("REDIS_URL", "")
        if not redis_url:
            # Construct from individual vars (matches docker-compose env)
            host = os.getenv("REDIS_HOST", "localhost")
            port = os.getenv("REDIS_PORT", "6379")
            redis_url = f"redis://{host}:{port}"
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(
                redis_url,
                decode_responses=False,
                socket_timeout=30,
                socket_connect_timeout=10,
            )
            await client.ping()
            log.info("worker.redis_connected", url=redis_url)
            return client
        except Exception as exc:
            log.warning("worker.redis_connect_failed", url=redis_url, error=str(exc))
            return None

    async def _ensure_consumer_group(self) -> None:
        try:
            await self._redis.xgroup_create(
                name=STREAM_KEY, groupname=GROUP_NAME, id="0", mkstream=True
            )
            log.info("worker.group_created", group=GROUP_NAME)
        except Exception:
            # Group already exists — that's fine
            pass

    async def _reclaim_stale(self, min_idle_ms: int = 60_000) -> list:
        """Reclaim messages from consumers that have been idle > 1 minute."""
        try:
            result = await self._redis.xautoclaim(
                name=STREAM_KEY,
                groupname=GROUP_NAME,
                consumername=CONSUMER_NAME,
                min_idle_time=min_idle_ms,
                start_id="0-0",
                count=10,
            )
            claimed = result[1] if result else []
            if claimed:
                log.info("worker.reclaimed", count=len(claimed))
                return claimed
        except Exception:
            pass  # xautoclaim requires Redis 6.2+ — skip silently on older versions
        return []

    async def _delivery_count(self, msg_id: bytes) -> int:
        try:
            pending = await self._redis.xpending_range(
                name=STREAM_KEY,
                groupname=GROUP_NAME,
                min=msg_id,
                max=msg_id,
                count=1,
            )
            if pending:
                return pending[0].get("times_delivered", 1)
        except Exception:
            pass
        return 1

    async def _dead_letter(self, msg_id: bytes, raw: dict, error: str) -> None:
        try:
            await self._redis.xadd(
                DLQ_KEY,
                {"original_msg_id": str(msg_id), "payload": json.dumps(raw), "error": error},
            )
            log.warning("worker.dead_lettered", msg_id=msg_id)
        except Exception as exc:
            log.error("worker.dlq_failed", error=str(exc))

    async def _notify_failed(self, document_id: str, error: str) -> None:
        try:
            from services.backend_callback import BackendCallback
            await BackendCallback().failed(document_id, error[:500])
        except Exception as exc:
            log.error("worker.notify_failed", document_id=document_id, error=str(exc))


# ── Singleton instance ─────────────────────────────────────────────────────────

_worker: DocumentPipelineWorker | None = None


def get_worker() -> DocumentPipelineWorker:
    global _worker
    if _worker is None:
        _worker = DocumentPipelineWorker()
    return _worker
