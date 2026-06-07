"""Document process router.

POST /process — called by Spring Boot AiServiceClient after a document is uploaded.

v2 behaviour: publishes to Redis Streams for durable async processing.
Fallback: if Redis is unavailable, falls back to direct async execution (v1 behaviour)
so the service degrades gracefully without breaking uploads.
"""

import json

from fastapi import APIRouter, BackgroundTasks

from models.schemas import ProcessDocumentRequest
from utils.logging import get_logger

router = APIRouter()
log = get_logger("routers.process")


@router.post("/process")
async def process_document(request: ProcessDocumentRequest, background_tasks: BackgroundTasks):
    """Accept a document processing request and queue it for execution."""
    published = await _publish_to_stream(request)
    if not published:
        # Graceful degradation: fall back to direct execution (v1 path)
        log.warning(
            "process.fallback_to_direct",
            document_id=request.documentId,
            reason="Redis Streams unavailable",
        )
        background_tasks.add_task(_process_direct, request)

    return {"status": "accepted", "documentId": request.documentId}


async def _publish_to_stream(request: ProcessDocumentRequest) -> bool:
    """Publish event to Redis Streams. Returns True on success."""
    try:
        from pipeline.worker import get_worker
        worker = get_worker()
        if worker._redis is None:
            return False

        payload = json.dumps({
            "documentId": request.documentId,
            "userId": request.userId,
            "objectKey": request.objectKey,
            "fileName": request.fileName,
            "fileType": request.fileType,
        })
        await worker._redis.xadd(
            "document.pipeline.jobs",
            {"documentId": request.documentId, "payload": payload},
        )
        log.info("process.published", document_id=request.documentId)
        return True
    except Exception as exc:
        log.error("process.publish_failed", document_id=request.documentId, error=str(exc))
        return False


async def _process_direct(request: ProcessDocumentRequest) -> None:
    """Direct execution fallback (v1 behaviour). Runs all stages inline."""
    from pipeline.context import PipelineContext
    from pipeline.stages import PIPELINE_STAGES, StageError
    from services.backend_callback import BackendCallback

    log.info("process.direct_start", document_id=request.documentId)
    callback = BackendCallback()
    try:
        ctx = PipelineContext(
            document_id=request.documentId,
            user_id=request.userId,
            object_key=request.objectKey,
            file_name=request.fileName,
            file_type=request.fileType,
        )
        for StageClass in PIPELINE_STAGES:
            stage = StageClass()
            ctx.start_stage(stage.name)
            ctx = await stage.execute(ctx)
            ctx.finish_stage(stage.name)
        log.info("process.direct_done", document_id=request.documentId, timings=ctx.stage_timings)
    except StageError as exc:
        log.error("process.direct_failed", document_id=request.documentId, stage=exc.stage, reason=exc.reason)
        await callback.failed(request.documentId, exc.reason)
    except Exception as exc:
        log.error("process.direct_error", document_id=request.documentId, error=str(exc), exc_info=True)
        await callback.failed(request.documentId, str(exc))
