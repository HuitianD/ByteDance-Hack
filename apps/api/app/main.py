"""Same-origin, single-worker ViralCraft application."""

from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse
import fcntl
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import Settings, get_settings
from app.runtime.store import Store, StoreError
from app.runtime.worker import Worker
from app.runtime.library import seed_library
from app.routes.workspace import router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    if settings.app_env == "production" and settings.legacy_local_api:
        raise RuntimeError("LEGACY_LOCAL_API must be false in production.")
    store = Store(settings.data_dir_path())
    seed_library(store)
    worker = Worker(settings, store)

    @asynccontextmanager
    async def lifespan(app):
        lock = None
        if settings.worker_enabled:
            lock = (settings.data_dir_path() / "worker.lock").open("a")
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                lock.close()
                raise RuntimeError(
                    "Only one ViralCraft worker may use a data directory."
                )
            await worker.start()
        try:
            yield
        finally:
            await worker.stop()
            if lock:
                lock.close()

    app = FastAPI(title="ViralCraft API", version="0.2.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.store = store
    app.state.worker = worker
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(StoreError)
    async def store_error(request, exc):
        return JSONResponse(status_code=exc.status, content={"detail": str(exc)})

    @app.middleware("http")
    async def origin_guard(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS") and origin:
            same = urlparse(origin).netloc == request.headers.get("host")
            if not same and origin not in settings.cors_origins_list():
                return JSONResponse(
                    status_code=403, content={"detail": "This origin is not allowed."}
                )
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/health")
    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "service": "viralcraft-api", "version": "0.2.0"}

    app.include_router(router)
    if settings.legacy_local_api:
        from app.routes.videos import router as videos
        from app.routes.storyboards import router as boards
        from app.routes.llm import router as llm

        @app.middleware("http")
        async def legacy_loopback(request: Request, call_next):
            if (
                request.url.path.startswith(("/videos", "/storyboards", "/llm"))
                and request.client
                and request.client.host not in ("127.0.0.1", "::1", "testclient")
            ):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Legacy endpoints are local-only."},
                )
            return await call_next(request)

        app.include_router(videos)
        app.include_router(boards)
        app.include_router(llm)
    dist = Path(settings.web_dist)
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app


app = create_app()
