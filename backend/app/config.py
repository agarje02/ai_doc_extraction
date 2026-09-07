"""Application configuration loaded from environment / .env.

All runtime behaviour (provider choice, OCR, chunking, storage) is config
driven so the same pipeline can run offline with the mock/Ollama providers or
against a hosted LLM without code changes.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_provider: str = Field(default="mock")
    llm_model: str = Field(default="gpt-4o-mini")
    llm_temperature: float = Field(default=0.0)
    llm_max_output_tokens: int = Field(default=2048)

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # OCR
    tesseract_cmd: str | None = None
    poppler_path: str | None = None
    ocr_enabled: bool = True
    ocr_min_chars: int = 20

    # Chunking
    chunk_max_tokens: int = 1200
    chunk_overlap_tokens: int = 150

    # Confidence
    confidence_review_threshold: float = 0.6

    # Storage
    database_url: str = "sqlite:///./ai_doc_extraction.db"
    storage_dir: str = "./storage"

    # API
    cors_origins: str = "http://localhost:3000"

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
