"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import documents, extractions, schemas
from app.config import get_settings
from app.models.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI Document Intelligence & Entity Extraction",
        version=__version__,
        description=(
            "Ingest documents, extract structured entities with an LLM, and "
            "review results with confidence scores and provenance."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "provider": settings.llm_provider, "version": __version__}

    app.include_router(documents.router)
    app.include_router(extractions.router)
    app.include_router(schemas.router)
    return app


app = create_app()
