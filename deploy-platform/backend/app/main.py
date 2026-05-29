import os
import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.config import settings
from app.database import Base, engine
from app.utils.logger import setup_logger, setup_access_logger

logger = setup_logger()
access_logger = setup_access_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Deploy Platform...")
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.log_dir, exist_ok=True)
    db_path = Path(settings.database_url.replace("sqlite:///", ""))
    os.makedirs(db_path.parent, exist_ok=True)
    logger.info("Upload, log, and data directories ensured.")

    # Recover orphaned tasks — mark any running/paused tasks as failed
    # since their in-memory coroutines are lost on restart.
    from app.database import SessionLocal
    from app.models.upgrade_task import UpgradeTask
    from app.models.task_step import TaskStep
    db = SessionLocal()
    try:
        orphaned = (
            db.query(UpgradeTask)
            .filter(UpgradeTask.status.in_(["running", "paused"]))
            .all()
        )
        if orphaned:
            logger.warning(f"Found {len(orphaned)} orphaned task(s) from previous run, marking as failed")
            for task in orphaned:
                task.status = "failed"
                task.finished_at = None  # will be set below
                # Mark running steps as failed
                for step in task.steps:
                    if step.status in ("running", "pending"):
                        step.status = "failed"
                        step.error_message = (step.error_message or "") + "\n服务器重启，任务中断"
                db.commit()
                logger.info(f"  Task {task.id} ({task.title}) recovered")
    finally:
        db.close()

    yield
    logger.info("Shutting down Deploy Platform.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# ── CORS ──

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Access log middleware ──


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = int((time.monotonic() - start) * 1000)
    client_ip = request.client.host if request.client else "-"
    access_logger.info(
        f"{client_ip} \"{request.method} {request.url.path}?{request.url.query}\" "
        f"{response.status_code} {duration_ms}ms"
    )
    return response

# ── Global exception handler ──


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}:\n{tb}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# ── Routes ──

app.include_router(api_router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok", "version": settings.app_version}


frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    # Static assets (JS, CSS, images)
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA fallback — serve index.html for all non-API, non-asset paths
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        index_path = frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Not Found")

    @app.get("/")
    async def serve_root():
        return FileResponse(frontend_dist / "index.html")
