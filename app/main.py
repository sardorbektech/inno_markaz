"""Inno Markaz - FastAPI Application Entry Point.

Conforms to AGENTS.md requirements for FastAPI backend and static frontend serving.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import router as api_router
from app.config.settings import settings
from app.db.postgres import db_manager
from app.llm.service import llm_service
from app.logging_config import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    logger.info("Starting Inno Markaz AI Agent application...")
    try:
        await db_manager.connect()
    except Exception as e:
        logger.warning(f"Could not connect to database on startup: {e}")

    try:
        llm_health = await llm_service.provider.check_health()
        logger.info(f"LLM Provider health check: {'OK' if llm_health else 'WARNING - not responding'}")
    except Exception as e:
        logger.warning(f"LLM Provider health check failed: {e}")

    yield

    logger.info("Shutting down Inno Markaz AI Agent application...")
    await db_manager.disconnect()


app = FastAPI(
    title="Inno Markaz AI Agent",
    description="PostgreSQL Database AI Agent with deterministic MCP pipeline and LLM abstraction.",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Static files directory
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Inno Markaz API is running. Static index.html not found."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
