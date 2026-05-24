import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.utils.config import logger, UPLOAD_DIR, REPORT_DIR, LOG_DIR
from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.services.database import connect_db, disconnect_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Initializing workspace folders...")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Connecting to database...")
    await connect_db()

    logger.info("FastAPI backend started successfully.")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Disconnecting from database...")
    await disconnect_db()

    logger.info("Cleaning up session uploads and generated reports...")
    try:
        if UPLOAD_DIR.exists():
            shutil.rmtree(UPLOAD_DIR)
            UPLOAD_DIR.mkdir()
        if REPORT_DIR.exists():
            shutil.rmtree(REPORT_DIR)
            REPORT_DIR.mkdir()
        logger.info("Cleanup completed successfully.")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


app = FastAPI(
    title="AI Multi-Agent Research & Report Platform",
    description="Professional enterprise AI multi-agent analyst dashboard and report generator.",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)   # /auth/register, /auth/login, /auth/me
app.include_router(router)        # /upload, /research, /download, /health, etc.
