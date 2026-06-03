from fastapi import APIRouter

from config import get_settings

router = APIRouter()


@router.get("/health")
def health():
    settings = get_settings()
    gemini_enabled = bool(settings.gemini_api_key)
    return {
        "status": "ok",
        "service": "insuramind-ai",
        "gemini_enabled": gemini_enabled,
        "gemini_fast_model": settings.gemini_fast_model,
        "gemini_reasoning_model": settings.gemini_reasoning_model,
        "embedding_model": settings.embedding_model,
        "embedding_dim": settings.embedding_dim,
    }
