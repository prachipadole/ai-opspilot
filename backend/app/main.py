"""
AI-OpsPilot – FastAPI application entry-point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.app.config import get_settings
from backend.app.database import engine, Base
from backend.app.api.routes import incidents, anomalies, logs, analysis, remediation, health

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup (dev convenience; use Alembic in prod)."""
    logger.info("Starting AI-OpsPilot backend …")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified / created.")

    # Auto-index sample runbooks into ChromaDB if available
    try:
        from backend.app.services.retriever import get_retriever
        count = get_retriever().index_runbooks("knowledge_base/sample_runbooks")
        logger.info(f"Auto-indexed {count} runbooks into ChromaDB on startup.")
    except Exception as exc:
        logger.warning(f"Runbook auto-indexing skipped (ChromaDB offline or initializing): {exc}")

    yield
    logger.info("Shutting down …")
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-powered IT operations platform: log ingestion, anomaly detection, "
        "LLM-based incident analysis, runbook retrieval and guided remediation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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
prefix = settings.api_prefix
app.include_router(health.router,      prefix=prefix, tags=["Health"])
app.include_router(logs.router,        prefix=prefix, tags=["Logs"])
app.include_router(incidents.router,   prefix=prefix, tags=["Incidents"])
app.include_router(anomalies.router,   prefix=prefix, tags=["Anomalies"])
app.include_router(analysis.router,    prefix=prefix, tags=["Analysis"])
app.include_router(remediation.router, prefix=prefix, tags=["Remediation"])


@app.get("/", include_in_schema=False)
async def root():
    return {"service": settings.app_name, "status": "running", "docs": "/docs"}
