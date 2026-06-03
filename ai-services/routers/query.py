from fastapi import APIRouter

from models.schemas import QueryRequest, QueryResponse
from services.backend_context_client import BackendContextClient
from services.reasoning_service import ReasoningService
from services.retrieval_service import RetrievalService
from services.verifier_service import VerifierService

router = APIRouter()

retrieval = RetrievalService()
reasoning = ReasoningService()
verifier = VerifierService()
backend_context = BackendContextClient()


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    rows = []
    try:
        context_rows = await backend_context.fetch_chunks(request.documentId)
        rows = retrieval.rank(request.question, context_rows, limit=8)
    except Exception:
        rows = retrieval.retrieve(request.documentId, request.userId, request.question, limit=8)
    answer, confidence, risk_alerts, intent = reasoning.answer(request.question, rows)
    verified = verifier.verify(answer, rows)
    if not verified:
        confidence = min(confidence, 0.55)
    return QueryResponse(
        answer=answer,
        confidence=round(confidence, 2),
        citations=retrieval.citations(rows[:5]),
        riskAlerts=risk_alerts,
        intent=intent,
        verified=verified,
    )
