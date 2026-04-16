"""LlamaIndex-based indexing service for crawled content."""

import logging
from typing import Optional

from llama_index.core import (
    Document,
    Settings as LlamaSettings,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI as OpenAILLM
from llama_index.vector_stores.chroma import ChromaVectorStore

from app.config import settings
from app.database.vector_store import vector_store_manager
from app.services.crawler_service import CrawledPage

logger = logging.getLogger(__name__)


class IndexerService:
    """Indexes crawled pages into the vector store via LlamaIndex."""

    def __init__(self) -> None:
        self._configured = False

    def _configure_llama_index(self) -> None:
        """Set global LlamaIndex defaults for LLM and embeddings."""
        if self._configured:
            return
        LlamaSettings.llm = OpenAILLM(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
        )
        LlamaSettings.embed_model = OpenAIEmbedding(
            model_name=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )
        LlamaSettings.chunk_size = settings.chunk_size
        LlamaSettings.chunk_overlap = settings.chunk_overlap
        self._configured = True

    def index_pages(
        self, website_url: str, pages: list[CrawledPage]
    ) -> VectorStoreIndex:
        """Convert crawled pages to LlamaIndex documents, chunk, and store."""
        self._configure_llama_index()

        documents = self._pages_to_documents(pages)
        logger.info("Indexing %d documents from %s", len(documents), website_url)

        chroma_collection = vector_store_manager.get_or_create_collection(website_url)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            transformations=[
                SentenceSplitter(
                    chunk_size=settings.chunk_size,
                    chunk_overlap=settings.chunk_overlap,
                )
            ],
        )

        logger.info("Indexing complete for %s", website_url)
        return index

    def load_index(self, website_url: str) -> Optional[VectorStoreIndex]:
        """Load an existing index from ChromaDB for a website."""
        self._configure_llama_index()

        if not vector_store_manager.collection_exists(website_url):
            return None

        chroma_collection = vector_store_manager.get_or_create_collection(website_url)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        index = VectorStoreIndex.from_vector_store(vector_store)
        return index

    @staticmethod
    def _pages_to_documents(pages: list[CrawledPage]) -> list[Document]:
        """Map crawled pages to LlamaIndex Document objects."""
        documents: list[Document] = []
        for page in pages:
            doc = Document(
                text=page.content,
                metadata={
                    "source_url": page.url,
                    "title": page.title,
                },
                excluded_llm_metadata_keys=["source_url"],
                excluded_embed_metadata_keys=["source_url"],
            )
            documents.append(doc)
        return documents


# Module-level singleton (lazy — no API key needed at import time)
indexer_service = IndexerService()
