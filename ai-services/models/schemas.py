from pydantic import BaseModel, Field
from typing import List, Optional


class ProcessDocumentRequest(BaseModel):
    documentId: str
    userId: str
    objectKey: str
    fileName: str
    fileType: str


class QueryRequest(BaseModel):
    documentId: str
    userId: str
    question: str = Field(min_length=1, max_length=1200)
    docType: Optional[str] = None


class Chunk(BaseModel):
    chunkIndex: int
    sectionType: str
    heading: Optional[str] = None
    parentHeading: Optional[str] = None
    text: str
    pageNumber: Optional[int] = None
    riskLevel: str = "low"
    riskScore: Optional[float] = None
    riskReason: Optional[str] = None
    importance: str = "normal"
    citationLabel: Optional[str] = None


class ExtractedEntity(BaseModel):
    entityType: str
    entityValue: str
    confidence: float = 0.8
    pageNumber: Optional[int] = None
    sourceChunkIndex: Optional[int] = None


class StructuredClause(BaseModel):
    """A fully extracted clause with confidence and provenance metadata."""
    clause_hash: str
    clause_type: str  # Dynamic — matches DTR section_taxonomy keys
    title: str
    value: str
    entities: List[ExtractedEntity] = []
    confidence: float  # overall extraction confidence (0.0–1.0)
    extraction_method: str  # "rules_spacy", "llm", "cache"
    risk_level: str = "low"
    risk_score: float = 0.0
    risk_reason: str = ""
    source_section: dict = {}


class AggregatorResult(BaseModel):
    """Document-level aggregation — fully DTR-driven.

    section_cards is keyed by the DTR section_taxonomy keys.
    For insurance_policy: {"coverage": [...], "exclusion": [...], ...}
    For loan_agreement:   {"terms": [...], "repayment": [...], ...}
    Any new doc type added to DTR automatically gets its own card categories.
    """
    document_summary: str = ""
    section_cards: dict = {}       # section_key → list of card dicts
    risk_summary: dict = {}        # aggregated risk across all sections
    entity_summary: dict = {}      # entity_name → extracted value (from entity_schema)


class Citation(BaseModel):
    citationLabel: Optional[str] = None
    pageNumber: Optional[int] = None
    sectionType: str
    heading: Optional[str] = None
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    citations: List[Citation]
    riskAlerts: List[str]
    intent: str
    verified: bool


class InternalIngestPayload(BaseModel):
    documentType: str = "policy"
    status: str = "READY"
    message: str = "Document processed"
    chunks: List[Chunk]
    entities: List[ExtractedEntity]
    # DTR-driven aggregator output (single JSONB-compatible field)
    aggregationResult: dict = {}

