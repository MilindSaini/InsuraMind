"""Pipeline stages — each stage receives a PipelineContext and returns it enriched.

Each stage is a self-contained async class with a single `execute(ctx)` method.
Failures raise `StageError`, which the worker catches and routes to the dead-letter queue.
"""

from __future__ import annotations

from utils.logging import get_logger
from pipeline.context import PipelineContext

log = get_logger("pipeline.stages")


class StageError(RuntimeError):
    """Raised by a stage when it cannot recover."""
    def __init__(self, stage: str, reason: str):
        super().__init__(f"[{stage}] {reason}")
        self.stage = stage
        self.reason = reason


# ─── Base ────────────────────────────────────────────────────────────────────

class BaseStage:
    name: str = "unnamed"

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        raise NotImplementedError


# ─── Stage 1: Download from MinIO ────────────────────────────────────────────

class DownloadStage(BaseStage):
    name = "download"

    def __init__(self):
        from services.storage_service import StorageService
        self._storage = StorageService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            import asyncio
            local_path = await asyncio.to_thread(
                self._storage.download, ctx.object_key, ctx.file_name
            )
            ctx.local_path = str(local_path)
            log.info("download.ok", document_id=ctx.document_id, path=ctx.local_path)
            return ctx
        except Exception as exc:
            raise StageError(self.name, f"Download failed: {exc}") from exc


# ─── Stage 2: OCR / text extraction ──────────────────────────────────────────

class OcrStage(BaseStage):
    name = "ocr"

    def __init__(self):
        from services.ocr_service import OcrService
        self._ocr = OcrService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.local_path:
            raise StageError(self.name, "local_path is missing — DownloadStage must run first")
        try:
            import asyncio
            from pathlib import Path
            pages = await asyncio.to_thread(self._ocr.extract_pages, Path(ctx.local_path))
            ctx.pages = pages
            ctx.full_text = "\n\n".join(p.get("text", "") for p in pages)
            if not ctx.full_text.strip():
                raise StageError(self.name, "No readable text was extracted from the document")
            log.info("ocr.ok", document_id=ctx.document_id, pages=len(pages))
            return ctx
        except StageError:
            raise
        except Exception as exc:
            raise StageError(self.name, f"OCR failed: {exc}") from exc


# ─── Stage 3: Document classification ────────────────────────────────────────

class ClassifierStage(BaseStage):
    name = "classify"

    def __init__(self):
        from services.classifier_service import ClassifierService
        self._classifier = ClassifierService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            import asyncio
            doc_type = await asyncio.to_thread(
                self._classifier.classify, ctx.full_text, ctx.file_name
            )
            ctx.document_type = doc_type
            log.info("classify.ok", document_id=ctx.document_id, document_type=doc_type)
            return ctx
        except Exception as exc:
            log.warning("classify.failed", document_id=ctx.document_id, error=str(exc))
            # Classification failure is non-fatal; default is already "policy"
            return ctx


# ─── Stage 4: Semantic chunking ───────────────────────────────────────────────

class ChunkerStage(BaseStage):
    name = "chunk"

    def __init__(self):
        from services.chunker_service import ChunkerService
        self._chunker = ChunkerService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            import asyncio
            chunks = await asyncio.to_thread(self._chunker.chunk, ctx.pages)
            if not chunks:
                raise StageError(self.name, "Chunker produced zero chunks — document may be empty")
            ctx.chunks = chunks
            log.info("chunk.ok", document_id=ctx.document_id, chunks=len(chunks))
            return ctx
        except StageError:
            raise
        except Exception as exc:
            raise StageError(self.name, f"Chunking failed: {exc}") from exc


# ─── Stage 5: Entity extraction ───────────────────────────────────────────────

class EntityExtractorStage(BaseStage):
    name = "extract"

    def __init__(self):
        from services.extractor_service import ExtractorService
        self._extractor = ExtractorService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            import asyncio
            entities = await asyncio.to_thread(self._extractor.extract, ctx.chunks)
            ctx.entities = entities
            log.info("extract.ok", document_id=ctx.document_id, entities=len(entities))
            return ctx
        except Exception as exc:
            log.warning("extract.failed", document_id=ctx.document_id, error=str(exc))
            # Entity extraction failure is non-fatal
            return ctx


# ─── Stage 6: Vector indexing ─────────────────────────────────────────────────

class VectorIndexStage(BaseStage):
    name = "index"

    def __init__(self):
        from services.retrieval_service import RetrievalService
        self._retrieval = RetrievalService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            import asyncio
            await asyncio.to_thread(
                self._retrieval.index, ctx.document_id, ctx.user_id, ctx.chunks
            )
            log.info("index.ok", document_id=ctx.document_id, vectors=len(ctx.chunks))
            return ctx
        except Exception as exc:
            raise StageError(self.name, f"Vector indexing failed: {exc}") from exc


# ─── Stage 7: Callback to Spring Boot ─────────────────────────────────────────

class BackendCallbackStage(BaseStage):
    name = "callback"

    def __init__(self):
        from services.backend_callback import BackendCallback
        self._callback = BackendCallback()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            payload = ctx.to_ingest_payload()
            await self._callback.ingest(ctx.document_id, payload)
            log.info("callback.ok", document_id=ctx.document_id)
            return ctx
        except Exception as exc:
            raise StageError(self.name, f"Backend callback failed: {type(exc).__name__}: {exc!r}") from exc


# ─── Ordered stage list (single source of truth) ──────────────────────────────

PIPELINE_STAGES: list[type[BaseStage]] = [
    DownloadStage,
    OcrStage,
    ClassifierStage,
    ChunkerStage,
    EntityExtractorStage,
    VectorIndexStage,
    BackendCallbackStage,
]
