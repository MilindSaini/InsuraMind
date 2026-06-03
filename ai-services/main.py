from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.health import router as health_router
from routers.process import router as process_router
from routers.query import router as query_router

app = FastAPI(title="InsuraMind AI Service", version="0.1.0")

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
    uvicorn.run(app, host="0.0.0.0", port=port)
