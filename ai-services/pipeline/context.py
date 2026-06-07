"""Pipeline context — shared state that flows through every stage."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from models.schemas import Chunk, ExtractedEntity, InternalIngestPayload


@dataclass
class PipelineContext:
    """Immutable-ish carrier that accumulates results as stages execute."""

    # ── Input (set from the trigger event) ──────────────────────────────────
    document_id: str
    user_id: str
    object_key: str
    file_name: str
    file_type: str

    # ── Stage outputs (populated progressively) ──────────────────────────────
    local_path: Optional[str] = None
    pages: list[dict[str, Any]] = field(default_factory=list)
    full_text: str = ""
    document_type: str = "policy"
    chunks: list[Chunk] = field(default_factory=list)
    entities: list[ExtractedEntity] = field(default_factory=list)

    # ── Diagnostics ───────────────────────────────────────────────────────────
    stage_timings: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    # ── Internal ──────────────────────────────────────────────────────────────
    _stage_start: float = field(default_factory=time.monotonic, repr=False)

    def start_stage(self, name: str) -> None:
        self._stage_start = time.monotonic()

    def finish_stage(self, name: str) -> None:
        self.stage_timings[name] = round(time.monotonic() - self._stage_start, 3)

    def to_ingest_payload(self) -> InternalIngestPayload:
        return InternalIngestPayload(
            documentType=self.document_type,
            status="READY",
            message=f"Processed {len(self.chunks)} chunks and {len(self.entities)} entities",
            chunks=self.chunks,
            entities=self.entities,
        )

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> "PipelineContext":
        return cls(
            document_id=event["documentId"],
            user_id=event["userId"],
            object_key=event["objectKey"],
            file_name=event["fileName"],
            file_type=event.get("fileType", "application/pdf"),
        )
