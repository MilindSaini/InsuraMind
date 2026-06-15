"""Pipeline stages — each stage receives a PipelineContext and returns it enriched.

Each stage is a self-contained async class with a single `execute(ctx)` method.
Failures raise `StageError`, which the worker catches and routes to the dead-letter queue.

Architecture v2:
  - SectionExtractorStage uses rule-first classification (LLM fallback only)
  - ParallelSectionProcessorStage: fan-out sections → process in parallel → fan-in
    (replaces ClauseExtractorStage + RiskTaggerStage + EntityExtractorStage + InsightRefinerStage)
  - BatchEmbedStage: batch embed all clauses at once
  - AggregatorStage: DTR-driven document-level summary + section cards
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


# ─── Stage 4: Section extraction (rule-first) ─────────────────────────────────

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


# ─── Stage 5: Parallel Section Processor (replaces 4 old stages) ─────────────

class ParallelSectionProcessorStage(BaseStage):
    """Fan-out sections → process in parallel → fan-in.

    For each section:
      - Run rules + spaCy first
      - Check confidence gate
      - Check clause hash cache
      - Run LLM only if needed
      - Create structured clause JSON

    Replaces: ClauseExtractorStage, RiskTaggerStage, EntityExtractorStage,
              InsightRefinerStage
    """
    name = "parallel_section_processor"

    def __init__(self):
        from services.section_processor import SectionProcessor
        from config import get_settings
        self._processor = SectionProcessor()
        self._settings = get_settings()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        import asyncio
        from models.schemas import ExtractedEntity

        if not ctx.sections:
            log.warning("parallel_section.no_sections", document_id=ctx.document_id)
            return ctx

        # Fan-out: process all sections in parallel (capped by max_section_workers)
        semaphore = asyncio.Semaphore(self._settings.max_section_workers)

        async def process_with_limit(section):
            async with semaphore:
                return await asyncio.wait_for(
                    self._processor.process(section, ctx.dtr_config),
                    timeout=self._settings.section_timeout_seconds,
                )

        tasks = [process_with_limit(section) for section in ctx.sections]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as exc:
            raise StageError(self.name, f"Parallel processing failed: {exc}") from exc

        # Fan-in: collect all results
        all_clauses = []
        all_entities = []
        llm_skipped = 0
        cache_hits = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log.warning(
                    "parallel_section.section_failed",
                    document_id=ctx.document_id,
                    section_index=i,
                    error=str(result),
                )
                continue

            all_clauses.extend(result.get("clauses", []))

            # Convert entity dicts back to ExtractedEntity objects
            for e_dict in result.get("entities", []):
                if isinstance(e_dict, dict):
                    try:
                        all_entities.append(ExtractedEntity(**e_dict))
                    except Exception:
                        pass
                elif isinstance(e_dict, ExtractedEntity):
                    all_entities.append(e_dict)

            if result.get("llm_skipped"):
                llm_skipped += 1
            if result.get("cache_hit"):
                cache_hits += 1

        ctx.structured_clauses = all_clauses
        ctx.clauses = all_clauses  # Backward compat
        ctx.entities = all_entities
        ctx.llm_calls_skipped = llm_skipped
        ctx.cache_hits = cache_hits

        log.info(
            "parallel_section.ok",
            document_id=ctx.document_id,
            total_sections=len(ctx.sections),
            total_clauses=len(all_clauses),
            total_entities=len(all_entities),
            llm_skipped=llm_skipped,
            cache_hits=cache_hits,
        )
        return ctx


# ─── Stage 6: Chunk builder ──────────────────────────────────────────────────

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


# ─── Stage 7: Batch embed all clauses ────────────────────────────────────────

class BatchEmbedStage(BaseStage):
    """Embed all chunks in a single batch call — cheaper than per-chunk."""
    name = "batch_embed"

    def __init__(self):
        from services.embedding_service import get_embedder
        self._embedder = get_embedder()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.chunks:
            return ctx
        try:
            import asyncio
            texts = [
                f"{chunk.sectionType}\n{chunk.heading or ''}\n{chunk.text}"
                for chunk in ctx.chunks
            ]
            ctx.embeddings = await asyncio.to_thread(self._embedder.embed, texts)
            log.info("batch_embed.ok", document_id=ctx.document_id, vectors=len(ctx.embeddings))
            return ctx
        except Exception as exc:
            raise StageError(self.name, f"Batch embedding failed: {exc}") from exc


# ─── Stage 8: Vector indexing (uses pre-computed embeddings) ──────────────────

class VectorIndexStage(BaseStage):
    name = "index"

    def __init__(self):
        from services.vector_store import VectorStore
        self._store = VectorStore()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.chunks:
            return ctx
        try:
            import asyncio
            if ctx.embeddings and len(ctx.embeddings) == len(ctx.chunks):
                # Use pre-computed embeddings from BatchEmbedStage
                await asyncio.to_thread(
                    self._store.upsert, ctx.document_id, ctx.user_id, ctx.chunks, ctx.embeddings
                )
            else:
                # Fallback: use RetrievalService.index which computes embeddings
                from services.retrieval_service import RetrievalService
                retrieval = RetrievalService()
                await asyncio.to_thread(
                    retrieval.index, ctx.document_id, ctx.user_id, ctx.chunks
                )
            log.info("index.ok", document_id=ctx.document_id, vectors=len(ctx.chunks))
            return ctx
        except Exception as exc:
            raise StageError(self.name, f"Vector indexing failed: {exc}") from exc


# ─── Stage 9: Document-level aggregation ──────────────────────────────────────

class AggregatorStage(BaseStage):
    """DTR-driven aggregation: document summary, section cards, risk summary.

    Runs ONCE per document. Reads section_taxonomy to decide what cards to build.
    Makes a single Gemini Flash call for the document summary.
    """
    name = "aggregator"

    def __init__(self):
        from services.aggregator_service import AggregatorService
        self._service = AggregatorService()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            entity_dicts = [e.model_dump() for e in ctx.entities]
            ctx.aggregator_result = await self._service.aggregate(
                ctx.structured_clauses, entity_dicts, ctx.dtr_config
            )
            log.info(
                "aggregator.ok",
                document_id=ctx.document_id,
                sections=len(ctx.aggregator_result.section_cards) if ctx.aggregator_result else 0,
            )
            return ctx
        except Exception as exc:
            log.warning("aggregator.failed", document_id=ctx.document_id, error=str(exc))
            # Aggregation failure is non-fatal — pipeline continues with what we have
            return ctx


# ─── Stage 10: Callback to Spring Boot ────────────────────────────────────────

class BackendCallbackStage(BaseStage):
    name = "callback"

    def __init__(self):
        from services.backend_callback import BackendCallback
        self._callback = BackendCallback()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        try:
            payload = ctx.to_ingest_payload()
            await self._callback.ingest(ctx.document_id, payload)
            log.info(
                "callback.ok",
                document_id=ctx.document_id,
                llm_skipped=ctx.llm_calls_skipped,
                cache_hits=ctx.cache_hits,
            )
            return ctx
        except Exception as exc:
            raise StageError(self.name, f"Backend callback failed: {type(exc).__name__}: {exc!r}") from exc


# ─── Ordered stage list (single source of truth) ──────────────────────────────

PIPELINE_STAGES: list[type[BaseStage]] = [
    DownloadStage,                    # 1. Download from MinIO
    DoclingStage,                     # 2. Parse with Docling
    ClassifierStage,                  # 3. Classify + load DTR config
    SectionExtractorStage,            # 4. Split into sections (rule-first)
    ParallelSectionProcessorStage,    # 5. Parallel: rules→cache→LLM per section
    ChunkBuilderStage,                # 6. Build Chunk models from clauses
    BatchEmbedStage,                  # 7. Batch embed all clauses
    VectorIndexStage,                 # 8. Upsert to Qdrant
    AggregatorStage,                  # 9. DTR-driven aggregation
    BackendCallbackStage,             # 10. Callback backend when done
]
