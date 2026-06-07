"""InsuraMind AI Service — entry point.

Startup sequence:
1. Configure structured logging.
2. Start the Redis Streams document pipeline worker (durable, at-least-once).
3. Include HTTP routers (health, process, query).

The /process endpoint still exists for backward-compatibility with the Spring Boot
AiServiceClient, but it now publishes to Redis Streams instead of running inline.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils.logging import configure_logging, get_logger
from pipeline.worker import get_worker
from routers.health import router as health_router
from routers.process import router as process_router
from routers.query import router as query_router

configure_logging()
log = get_logger("insuramind.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = get_worker()
    await worker.start()
    log.info("app.started")
    yield
    await worker.stop()
    log.info("app.stopped")


app = FastAPI(
    title="InsuraMind AI Service",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(process_router)
app.include_router(query_router)


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("AI_SERVICE_PORT", os.getenv("PORT", "8003")))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
