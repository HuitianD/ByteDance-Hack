"""ViralCraft API entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core.config import get_settings
from app.routes.llm import router as llm_router
from app.routes.videos import router as videos_router

settings = get_settings()

app = FastAPI(
    title="ViralCraft API",
    description="Backend for the ViralCraft short video structure transfer engine.",
    version="0.0.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="viralcraft-api", version="0.0.1")


app.include_router(llm_router)
app.include_router(videos_router)

# Serve files under DATA_DIR (frames, renders, etc.) at /static/...
# Read-only; only files written by the API are exposed.
data_dir = settings.data_dir_path()
data_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=data_dir, check_dir=False), name="static")
