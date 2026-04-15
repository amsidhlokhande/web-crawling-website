"""Pydantic request/response schemas for the API."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class CrawlStatus(str, Enum):
    """Status of a crawl job."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Crawl Schemas ──


class CrawlRequest(BaseModel):
    """Request body to start a new crawl job."""

    url: HttpUrl = Field(..., description="The website URL to crawl")
    max_pages: Optional[int] = Field(
        None, ge=1, le=10000, description="Maximum number of pages to crawl"
    )
    max_depth: Optional[int] = Field(
        None, ge=1, le=10, description="Maximum crawl depth"
    )


class CrawlResponse(BaseModel):
    """Response after starting a crawl job."""

    crawl_id: str = Field(..., description="Unique identifier for the crawl job")
    url: str = Field(..., description="The website URL being crawled")
    status: CrawlStatus = Field(..., description="Current status of the crawl")
    message: str = Field(..., description="Human-readable status message")


class CrawlStatusResponse(BaseModel):
    """Response for crawl status check."""

    crawl_id: str
    url: str
    status: CrawlStatus
    pages_crawled: int = 0
    pages_indexed: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


# ── Query Schemas ──


class QueryRequest(BaseModel):
    """Request body to query crawled content."""

    question: str = Field(
        ..., min_length=1, max_length=2000, description="The question to ask"
    )
    website_url: Optional[str] = Field(
        None, description="Filter to a specific website (optional)"
    )
    top_k: int = Field(
        5, ge=1, le=20, description="Number of relevant chunks to retrieve"
    )


class SourceDocument(BaseModel):
    """A source document referenced in a query response."""

    page_url: str
    content_snippet: str
    relevance_score: Optional[float] = None


class QueryResponse(BaseModel):
    """Response to a query."""

    answer: str = Field(..., description="The generated answer")
    sources: list[SourceDocument] = Field(
        default_factory=list, description="Source documents used to generate the answer"
    )
    question: str = Field(..., description="The original question")


# ── Website Schemas ──


class WebsiteInfo(BaseModel):
    """Information about a crawled website."""

    website_id: str
    url: str
    status: CrawlStatus
    pages_crawled: int = 0
    pages_indexed: int = 0
    crawled_at: Optional[datetime] = None


class WebsiteListResponse(BaseModel):
    """List of all crawled websites."""

    websites: list[WebsiteInfo] = Field(default_factory=list)
    total: int = 0


class DeleteWebsiteResponse(BaseModel):
    """Response after deleting a website."""

    website_id: str
    message: str
