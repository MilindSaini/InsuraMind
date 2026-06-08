from functools import lru_cache
from pydantic import BaseModel
import os
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_env_file(Path(__file__).resolve().parents[1] / ".env")
_load_env_file(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseModel):
    backend_base_url: str = os.getenv("BACKEND_BASE_URL", "http://localhost:8080/api")
    internal_token: str = os.getenv("INTERNAL_TOKEN", os.getenv("APP_INTERNAL_TOKEN", "dev-internal-token-change-me"))

    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "insuramind")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "insuramind-secret")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "insuramind-documents")

    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "insuramind_chunks")

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_fast_model: str = os.getenv("GEMINI_FAST_MODEL", "gemini-2.5-flash")
    gemini_reasoning_model: str = os.getenv("GEMINI_REASONING_MODEL", "gemini-2.5-pro")
    gemini_verifier_model: str = os.getenv(
        "GEMINI_VERIFIER_MODEL",
        os.getenv("GEMINI_FAST_MODEL", "gemini-2.5-flash"),
    )

    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "1024"))
    fallback_index_path: str = os.getenv("FALLBACK_INDEX_PATH", "storage/vector_index.json")

    # DTR (Document Type Registry)
    dtr_cache_ttl_seconds: int = int(os.getenv("DTR_CACHE_TTL_SECONDS", "3600"))
    dtr_enable_llm_extraction: bool = os.getenv("DTR_ENABLE_LLM_EXTRACTION", "false").lower() == "true"


@lru_cache
def get_settings() -> Settings:
    return Settings()
