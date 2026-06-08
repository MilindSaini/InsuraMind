"""Query router — DTR-aware.

Looks up the document's doc_type, loads the DTR config once,
and passes it through all service calls for config-driven behavior.
"""

from fastapi import APIRouter

from dtr.registry import get_registry
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
registry = get_registry()


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    # Load DTR config for this document's type
    doc_type = getattr(request, "docType", None) or None
    config = None

    # Try to get doc_type from document metadata via backend
    if not doc_type:
        try:
            doc_type = await _get_doc_type(request.documentId)
        except Exception:
            pass

    if doc_type:
        config = registry.get(doc_type)

    # Retrieve evidence
    rows = []
    try:
        context_rows = await backend_context.fetch_chunks(request.documentId)
        rows = retrieval.rank(request.question, context_rows, limit=8, config=config)
    except Exception:
        rows = retrieval.retrieve(
            request.documentId, request.userId, request.question,
            limit=8, config=config,
        )

    # Generate answer with DTR config
    answer, confidence, risk_alerts, intent = reasoning.answer(
        request.question, rows, config=config,
    )

    # Verify with DTR config
    verified = verifier.verify(answer, rows, config=config)
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


async def _get_doc_type(document_id: str) -> str | None:
    """Fetch doc_type from backend document metadata."""
    import httpx
    from config import get_settings

    settings = get_settings()
    url = f"{settings.backend_base_url.rstrip('/')}/internal/documents/{document_id}/chunks"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                url,
                headers={"X-Internal-Token": settings.internal_token},
            )
            if response.status_code < 400:
                chunks = response.json()
                # The doc type is typically inferred from section patterns;
                # here we return None and rely on request-level doc_type
                return None
    except Exception:
        pass
    return None
