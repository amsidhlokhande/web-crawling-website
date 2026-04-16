"""API routes for website crawling operations."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models.schemas import (
    CrawlRequest,
    CrawlResponse,
    CrawlStatus,
    CrawlStatusResponse,
    DeleteWebsiteResponse,
    WebsiteInfo,
    WebsiteListResponse,
)
from app.services.crawler_service import CrawlerService
from app.services.indexer_service import indexer_service
from app.database.vector_store import vector_store_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crawl", tags=["Crawl"])

# In-memory job tracker (swap for Redis/DB in production)
_crawl_jobs: dict[str, CrawlStatusResponse] = {}


def _run_crawl_job(
    crawl_id: str, url: str, max_pages: int | None, max_depth: int | None
) -> None:
    """Background task that performs the crawl and indexes results."""
    job = _crawl_jobs[crawl_id]
    job.status = CrawlStatus.IN_PROGRESS
    job.started_at = datetime.now(timezone.utc)

    try:
        crawler = CrawlerService(max_pages=max_pages, max_depth=max_depth)
        pages = crawler.crawl(url)
        job.pages_crawled = len(pages)

        if pages:
            indexer_service.index_pages(url, pages)
            job.pages_indexed = len(pages)

        job.status = CrawlStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        logger.info("Crawl job %s completed: %d pages", crawl_id, len(pages))

    except Exception as exc:
        logger.exception("Crawl job %s failed", crawl_id)
        job.status = CrawlStatus.FAILED
        job.error = str(exc)
        job.completed_at = datetime.now(timezone.utc)


@router.post("", response_model=CrawlResponse)
async def start_crawl(
    request: CrawlRequest, background_tasks: BackgroundTasks
) -> CrawlResponse:
    """Start crawling a website in the background.

    The crawl runs asynchronously. Use the returned ``crawl_id`` to poll
    for progress via ``GET /crawl/{crawl_id}/status``.
    """
    crawl_id = str(uuid.uuid4())
    url = str(request.url).rstrip("/")

    _crawl_jobs[crawl_id] = CrawlStatusResponse(
        crawl_id=crawl_id,
        url=url,
        status=CrawlStatus.PENDING,
    )

    background_tasks.add_task(
        _run_crawl_job, crawl_id, url, request.max_pages, request.max_depth
    )

    return CrawlResponse(
        crawl_id=crawl_id,
        url=url,
        status=CrawlStatus.PENDING,
        message=f"Crawl job started for {url}",
    )


@router.get("/{crawl_id}/status", response_model=CrawlStatusResponse)
async def get_crawl_status(crawl_id: str) -> CrawlStatusResponse:
    """Check the status of a crawl job."""
    job = _crawl_jobs.get(crawl_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Crawl job not found")
    return job


@router.get("/websites", response_model=WebsiteListResponse)
async def list_websites() -> WebsiteListResponse:
    """List all crawled and indexed websites."""
    collections = vector_store_manager.list_collections()
    websites = [
        WebsiteInfo(
            website_id=col["name"],
            url=col["source_url"],
            status=CrawlStatus.COMPLETED,
            pages_indexed=col["count"],
        )
        for col in collections
    ]
    return WebsiteListResponse(websites=websites, total=len(websites))


@router.delete("/websites/{website_id}", response_model=DeleteWebsiteResponse)
async def delete_website(website_id: str) -> DeleteWebsiteResponse:
    """Delete a crawled website and its indexed data."""
    collections = vector_store_manager.list_collections()
    target = next((c for c in collections if c["name"] == website_id), None)

    if target is None:
        raise HTTPException(status_code=404, detail="Website not found")

    vector_store_manager.delete_collection(target["source_url"])
    return DeleteWebsiteResponse(
        website_id=website_id,
        message=f"Website '{target['source_url']}' and its indexed data have been deleted.",
    )
