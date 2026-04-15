"""Query service for interactive Q&A over crawled content."""

import logging
from typing import Optional

from llama_index.core import VectorStoreIndex

from app.database.vector_store import vector_store_manager
from app.models.schemas import QueryResponse, SourceDocument
from app.services.indexer_service import indexer_service

logger = logging.getLogger(__name__)


class QueryService:
    """Handles natural-language queries against indexed website content."""

    def query(
        self,
        question: str,
        website_url: Optional[str] = None,
        top_k: int = 5,
    ) -> QueryResponse:
        """Ask a question and receive a synthesised answer with sources.

        Parameters
        ----------
        question:
            The natural-language question.
        website_url:
            If provided, restrict the search to this website's index.
        top_k:
            Number of relevant chunks to retrieve.
        """
        index = self._get_index(website_url)
        if index is None:
            return QueryResponse(
                answer="No indexed content found. Please crawl a website first.",
                sources=[],
                question=question,
            )

        query_engine = index.as_query_engine(similarity_top_k=top_k)
        response = query_engine.query(question)

        sources = self._extract_sources(response)

        return QueryResponse(
            answer=str(response),
            sources=sources,
            question=question,
        )

    # ── Helpers ──

    @staticmethod
    def _get_index(website_url: Optional[str]) -> Optional[VectorStoreIndex]:
        """Load the vector index, optionally filtering by website."""
        if website_url:
            return indexer_service.load_index(website_url)

        # No specific URL — use the first available collection
        all_collections = vector_store_manager.list_collections()
        if not all_collections:
            return None

        first_url = all_collections[0].get("source_url", "")
        if first_url:
            return indexer_service.load_index(first_url)
        return None

    @staticmethod
    def _extract_sources(response: object) -> list[SourceDocument]:
        """Pull source metadata from a LlamaIndex response."""
        sources: list[SourceDocument] = []
        source_nodes = getattr(response, "source_nodes", [])
        for node in source_nodes:
            metadata = node.node.metadata if hasattr(node, "node") else {}
            snippet = node.node.get_content()[:300] if hasattr(node, "node") else ""
            sources.append(
                SourceDocument(
                    page_url=metadata.get("source_url", "unknown"),
                    content_snippet=snippet,
                    relevance_score=node.score if hasattr(node, "score") else None,
                )
            )
        return sources


# Module-level singleton
query_service = QueryService()
