"""Pipeline stages — each stage receives a PipelineContext and returns it enriched.

Each stage is a self-contained async class with a single `execute(ctx)` method.
Failures raise `StageError`, which the worker catches and routes to the dead-letter queue.

DTR integration:
  - ClassifierStage loads the DTR config and attaches it to ctx.dtr_config.
  - ChunkerStage and EntityExtractorStage consume ctx.dtr_config.
  - Download, OCR, VectorIndex, Callback stages are universal (no config needed).
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


# ─── Stage 2: Docling Document Extraction ──────────────────────────────────────────

class DoclingStage(BaseStage):
    name = "docling"

    def __init__(self):
        from services.docling_service import DoclingService
        self._docling = DoclingService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.local_path:
            raise StageError(self.name, "local_path is missing — DownloadStage must run first")
        try:
            import asyncio
            from pathlib import Path
            docling_doc = await asyncio.to_thread(self._docling.convert, Path(ctx.local_path))
            ctx.docling_doc = docling_doc
            
            # Export basic markdown for legacy full_text requirements or logging
            ctx.full_text = docling_doc.export_to_markdown()
            
            log.info("docling.ok", document_id=ctx.document_id, text_length=len(ctx.full_text))
            return ctx
        except Exception as exc:
            raise StageError(self.name, f"Docling conversion failed: {exc}") from exc


# ─── Stage 3: Document classification + DTR config loading ───────────────────

class ClassifierStage(BaseStage):
    name = "classify"

    def __init__(self):
        from services.classifier_service import ClassifierService
        from dtr.registry import get_registry
        self._classifier = ClassifierService()
        self._registry = get_registry()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            import asyncio
            doc_type = await asyncio.to_thread(
                self._classifier.classify, ctx.full_text, ctx.file_name
            )
            ctx.document_type = doc_type

            # Load DTR config for this doc type
            ctx.dtr_config = self._registry.get(doc_type)
            log.info(
                "classify.ok",
                document_id=ctx.document_id,
                document_type=doc_type,
                dtr_loaded=ctx.dtr_config is not None,
            )
            return ctx
        except Exception as exc:
            log.warning("classify.failed", document_id=ctx.document_id, error=str(exc))
            # Classification failure is non-fatal; default DTR config used
            ctx.dtr_config = self._registry.get(ctx.document_type)
            return ctx


# ─── Stage 4: Section extraction ───────────────────────────────────────────────

class SectionExtractorStage(BaseStage):
    name = "section_extractor"

    def __init__(self):
        from services.section_extractor_service import SectionExtractorService
        self._service = SectionExtractorService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            ctx.sections = await self._service.extract(ctx.docling_doc, ctx.dtr_config)
            log.info("section.ok", document_id=ctx.document_id, sections=len(ctx.sections))
            return ctx
        except Exception as exc:
            raise StageError(self.name, f"Section extraction failed: {exc}") from exc

# ─── Stage 4.1: Clause extraction ──────────────────────────────────────────────

class ClauseExtractorStage(BaseStage):
    name = "clause_extractor"

    def __init__(self):
        from services.clause_extractor_service import ClauseExtractorService
        self._service = ClauseExtractorService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            ctx.clauses = await self._service.extract(ctx.sections, ctx.dtr_config)
            log.info("clause.ok", document_id=ctx.document_id, clauses=len(ctx.clauses))
            return ctx
        except Exception as exc:
            raise StageError(self.name, f"Clause extraction failed: {exc}") from exc

# ─── Stage 4.2: Chunk builder ──────────────────────────────────────────────────

class ChunkBuilderStage(BaseStage):
    name = "chunk_builder"

    def __init__(self):
        from services.chunk_builder_service import ChunkBuilderService
        self._service = ChunkBuilderService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            import asyncio
            ctx.chunks = await asyncio.to_thread(self._service.build_chunks, ctx.clauses)
            log.info("chunk_builder.ok", document_id=ctx.document_id, chunks=len(ctx.chunks))
            return ctx
        except Exception as exc:
            raise StageError(self.name, f"Chunk building failed: {exc}") from exc


# ─── Stage 4.5: Insight refinement ──────────────────────────────────────────────

class InsightRefinerStage(BaseStage):
    name = "refine"

    def __init__(self):
        from services.refiner_service import RefinerService
        self._refiner = RefinerService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            import asyncio
            chunks = await self._refiner.refine(ctx.chunks, ctx.dtr_config)
            ctx.chunks = chunks
            log.info("refine.ok", document_id=ctx.document_id, chunks=len(chunks))
            return ctx
        except Exception as exc:
            log.warning("refine.failed", document_id=ctx.document_id, error=str(exc))
            return ctx


# ─── Stage 4.6: Risk Tagging ───────────────────────────────────────────────────

class RiskTaggerStage(BaseStage):
    name = "risk_tagger"

    def __init__(self):
        from services.risk_tagger_service import RiskTaggerService
        self._service = RiskTaggerService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            ctx.clauses = await self._service.tag(ctx.clauses)
            log.info("risk_tagger.ok", document_id=ctx.document_id)
            return ctx
        except Exception as exc:
            log.warning("risk_tagger.failed", document_id=ctx.document_id, error=str(exc))
            return ctx


# ─── Stage 5: Entity extraction ───────────────────────────────────────────────

class EntityExtractorStage(BaseStage):
    name = "extract"

    def __init__(self):
        from services.extractor_service import ExtractorService
        self._extractor = ExtractorService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            import asyncio
            entities = await asyncio.to_thread(
                self._extractor.extract, ctx.clauses, ctx.dtr_config
            )
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
    DoclingStage,
    ClassifierStage,
    SectionExtractorStage,
    ClauseExtractorStage,
    RiskTaggerStage,
    EntityExtractorStage,
    ChunkBuilderStage,
    InsightRefinerStage,
    VectorIndexStage,
    BackendCallbackStage,
]
