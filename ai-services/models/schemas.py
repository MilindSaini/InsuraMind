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


class Chunk(BaseModel):
    chunkIndex: int
    sectionType: str
    heading: Optional[str] = None
    text: str
    pageNumber: Optional[int] = None
    riskLevel: str = "low"
    importance: str = "normal"
    citationLabel: Optional[str] = None


class ExtractedEntity(BaseModel):
    entityType: str
    entityValue: str
    confidence: float = 0.8
    pageNumber: Optional[int] = None
    sourceChunkIndex: Optional[int] = None


class Citation(BaseModel):
    citationLabel: Optional[str] = None
    pageNumber: Optional[int] = None
    sectionType: str
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
