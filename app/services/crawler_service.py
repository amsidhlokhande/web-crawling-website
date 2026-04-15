"""Web crawling service using Selenium (headless) and BeautifulSoup."""

import logging
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.config import settings

logger = logging.getLogger(__name__)


class CrawledPage:
    """Represents a single crawled web page."""

    def __init__(self, url: str, title: str, content: str, links: list[str]) -> None:
        self.url = url
        self.title = title
        self.content = content
        self.links = links

    def __repr__(self) -> str:
        return f"CrawledPage(url={self.url!r}, title={self.title!r})"


class CrawlerService:
    """Generic website crawler that extracts text content from pages."""

    def __init__(
        self,
        max_pages: int | None = None,
        max_depth: int | None = None,
    ) -> None:
        self.max_pages = max_pages or settings.crawl_max_pages
        self.max_depth = max_depth or settings.crawl_max_depth
        self.delay = settings.crawl_delay_seconds
        self.timeout = settings.crawl_timeout_seconds
        self.respect_robots = settings.crawl_respect_robots_txt

        self._visited: set[str] = set()
        self._pages: list[CrawledPage] = []
        self._robots_parser: RobotFileParser | None = None
        self._base_domain: str = ""

    # ── Public API ──

    def crawl(self, start_url: str) -> list[CrawledPage]:
        """Crawl *start_url* and return all discovered pages."""
        parsed = urlparse(start_url)
        self._base_domain = parsed.netloc
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        if self.respect_robots:
            self._load_robots(base_url)

        driver = self._create_driver()
        try:
            self._crawl_recursive(driver, start_url, depth=0)
        finally:
            driver.quit()

        logger.info("Crawl complete: %d pages from %s", len(self._pages), start_url)
        return self._pages

    # ── Internals ──

    def _create_driver(self) -> webdriver.Chrome:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (compatible; WebCrawlerBot/1.0)")
        service = Service()
        return webdriver.Chrome(service=service, options=options)

    def _load_robots(self, base_url: str) -> None:
        robots_url = f"{base_url}/robots.txt"
        self._robots_parser = RobotFileParser()
        self._robots_parser.set_url(robots_url)
        try:
            self._robots_parser.read()
            logger.info("Loaded robots.txt from %s", robots_url)
        except Exception:
            logger.warning("Could not load robots.txt from %s", robots_url)
            self._robots_parser = None

    def _is_allowed(self, url: str) -> bool:
        if self._robots_parser is None:
            return True
        return self._robots_parser.can_fetch("*", url)

    def _normalize_url(self, url: str) -> str:
        """Strip fragments and trailing slashes for deduplication."""
        parsed = urlparse(url)
        clean = parsed._replace(fragment="")
        result = clean.geturl().rstrip("/")
        return result

    def _is_same_domain(self, url: str) -> bool:
        return urlparse(url).netloc == self._base_domain

    def _is_valid_page_url(self, url: str) -> bool:
        """Filter out non-HTML resources."""
        skip_extensions = {
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".svg",
            ".webp",
            ".mp4",
            ".mp3",
            ".zip",
            ".tar",
            ".gz",
            ".css",
            ".js",
            ".ico",
            ".woff",
            ".woff2",
            ".ttf",
            ".eot",
        }
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        return not any(path_lower.endswith(ext) for ext in skip_extensions)

    def _extract_page(self, driver: webdriver.Chrome, url: str) -> CrawledPage | None:
        """Load a URL in Selenium and extract content with BeautifulSoup."""
        try:
            driver.set_page_load_timeout(self.timeout)
            driver.get(url)

            WebDriverWait(driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            # Allow JS rendering time
            time.sleep(0.5)

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # Remove non-content elements
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                tag.decompose()

            title = (
                soup.title.string.strip() if soup.title and soup.title.string else url
            )
            text = self._clean_text(soup.get_text(separator="\n"))

            # Extract links
            links: list[str] = []
            for anchor in soup.find_all("a", href=True):
                href = anchor["href"]
                absolute = urljoin(url, href)
                links.append(self._normalize_url(absolute))

            if not text.strip():
                logger.debug("Skipping empty page: %s", url)
                return None

            return CrawledPage(url=url, title=title, content=text, links=links)

        except Exception as exc:
            logger.warning("Failed to crawl %s: %s", url, exc)
            return None

    @staticmethod
    def _clean_text(text: str) -> str:
        """Collapse whitespace while preserving paragraph structure."""
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        return "\n".join(lines)

    def _crawl_recursive(self, driver: webdriver.Chrome, url: str, depth: int) -> None:
        """Depth-first crawl with limits."""
        url = self._normalize_url(url)

        if url in self._visited:
            return
        if len(self._pages) >= self.max_pages:
            return
        if depth > self.max_depth:
            return
        if not self._is_same_domain(url):
            return
        if not self._is_valid_page_url(url):
            return
        if not self._is_allowed(url):
            logger.debug("Blocked by robots.txt: %s", url)
            return

        self._visited.add(url)
        logger.info(
            "Crawling [%d/%d] depth=%d: %s",
            len(self._pages) + 1,
            self.max_pages,
            depth,
            url,
        )

        page = self._extract_page(driver, url)
        if page is None:
            return

        self._pages.append(page)

        # Polite delay
        time.sleep(self.delay)

        # Follow discovered links
        for link in page.links:
            if len(self._pages) >= self.max_pages:
                break
            self._crawl_recursive(driver, link, depth + 1)
