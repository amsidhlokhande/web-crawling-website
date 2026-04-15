"""API routes for querying crawled website content."""

import logging

from fastapi import APIRouter

from app.models.schemas import QueryRequest, QueryResponse
from app.services.query_service import query_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("", response_model=QueryResponse)
def query_content(request: QueryRequest) -> QueryResponse:
    """Ask a natural-language question about crawled website content.

    Optionally filter to a specific website by providing ``website_url``.
    """
    logger.info("Query received: %s", request.question[:100])
    website_url = request.website_url.rstrip("/") if request.website_url else None
    response = query_service.query(
        question=request.question,
        website_url=website_url,
        top_k=request.top_k,
    )
    return response
