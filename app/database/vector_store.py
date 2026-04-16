"""ChromaDB vector store abstraction layer."""

import hashlib
import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manages ChromaDB collections for storing crawled website content."""

    def __init__(self) -> None:
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info("ChromaDB initialized at %s", persist_dir)

    @staticmethod
    def _collection_name(url: str) -> str:
        """Generate a deterministic collection name from a URL.

        ChromaDB collection names must be 3-63 characters, start/end with
        alphanumeric, and contain only alphanumerics, underscores, or hyphens.
        """
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        prefix = settings.chroma_collection_prefix
        return f"{prefix}_{url_hash}"

    def get_or_create_collection(self, url: str) -> chromadb.Collection:
        """Return (or create) the collection for a given website URL."""
        name = self._collection_name(url)
        collection = self._client.get_or_create_collection(
            name=name,
            metadata={"source_url": url},
        )
        logger.info("Using collection '%s' for %s", name, url)
        return collection

    def delete_collection(self, url: str) -> None:
        """Delete the collection associated with a website URL."""
        name = self._collection_name(url)
        try:
            self._client.delete_collection(name=name)
            logger.info("Deleted collection '%s'", name)
        except ValueError:
            logger.warning("Collection '%s' not found for deletion", name)

    def collection_exists(self, url: str) -> bool:
        """Check whether a collection exists for the given URL."""
        name = self._collection_name(url)
        existing = [c.name for c in self._client.list_collections()]
        return name in existing

    def list_collections(self) -> list[dict]:
        """Return metadata for every stored collection."""
        results: list[dict] = []
        for col in self._client.list_collections():
            if col.name.startswith(settings.chroma_collection_prefix):
                meta = col.metadata or {}
                results.append(
                    {
                        "name": col.name,
                        "source_url": meta.get("source_url", ""),
                        "count": col.count(),
                    }
                )
        return results

    @property
    def client(self) -> chromadb.ClientAPI:
        """Expose the underlying ChromaDB client."""
        return self._client


# Module-level singleton
vector_store_manager = VectorStoreManager()
