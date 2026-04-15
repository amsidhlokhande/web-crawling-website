"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    app_name: str = "Web Crawling Q&A"
    app_version: str = "1.0.0"
    debug: bool = False

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # ChromaDB
    chroma_persist_dir: str = str(Path.home() / ".webcrawler" / "chroma_db")
    chroma_collection_prefix: str = "website"

    # Crawler
    crawl_max_pages: int = 100
    crawl_max_depth: int = 3
    crawl_delay_seconds: float = 1.0
    crawl_timeout_seconds: int = 30
    crawl_respect_robots_txt: bool = True

    # Indexing
    chunk_size: int = 1024
    chunk_overlap: int = 200

    # API
    api_prefix: str = "/api/v1"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()
