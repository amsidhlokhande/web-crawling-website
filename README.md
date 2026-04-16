# Web Crawling Q&A Application

A generic, configurable web crawling solution that crawls any website, stores its content in a vector database (ChromaDB), indexes it with LlamaIndex, and provides an interactive REST API for natural-language Q&A.

## Architecture

The project follows a **layered separation of concerns**:

```
app/
├── main.py              # FastAPI entry point
├── config.py            # Centralised settings (env vars)
├── routes/              # API endpoints
│   ├── crawl_routes.py  # Crawl & website management
│   └── query_routes.py  # Q&A queries
├── services/            # Business logic
│   ├── crawler_service.py   # Selenium headless crawler
│   ├── indexer_service.py   # LlamaIndex indexing
│   └── query_service.py     # Q&A query engine
├── database/            # Persistence
│   └── vector_store.py  # ChromaDB abstraction
└── models/              # Data contracts
    └── schemas.py       # Pydantic request/response models
```

## Tech Stack

| Component       | Technology                        |
|----------------|-----------------------------------|
| Web Framework  | FastAPI                           |
| Web Crawling   | Selenium (headless) + BeautifulSoup |
| Vector DB      | ChromaDB                          |
| Indexing & LLM | LlamaIndex + OpenAI               |
| Validation     | Pydantic v2                       |

## Quick Start

### Prerequisites

- Python 3.10+
- Google Chrome (for Selenium headless crawling)
- ChromeDriver (matching your Chrome version)
- An OpenAI API key

### Installation

```bash
# Clone the repository
git clone https://github.com/amsidhlokhande/web-crawling-website.git
cd web-crawling-website

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

### Run the Server

```bash
python run.py
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## API Endpoints

### Crawl

| Method   | Endpoint                          | Description                    |
|----------|-----------------------------------|--------------------------------|
| `POST`   | `/api/v1/crawl`                   | Start crawling a website       |
| `GET`    | `/api/v1/crawl/{crawl_id}/status` | Check crawl job status         |
| `GET`    | `/api/v1/crawl/websites`          | List all crawled websites      |
| `DELETE` | `/api/v1/crawl/websites/{id}`     | Delete a website and its data  |

### Query

| Method | Endpoint           | Description                          |
|--------|--------------------|--------------------------------------|
| `POST` | `/api/v1/query`    | Ask a question about crawled content |

## Usage Examples

### 1. Crawl a Website

```bash
curl -X POST http://localhost:8000/api/v1/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.fidante.com/",
    "max_pages": 50,
    "max_depth": 2
  }'
```

Response:
```json
{
  "crawl_id": "abc123-...",
  "url": "https://www.fidante.com",
  "status": "pending",
  "message": "Crawl job started for https://www.fidante.com"
}
```

### 2. Check Crawl Status

```bash
curl http://localhost:8000/api/v1/crawl/{crawl_id}/status
```

### 3. Ask a Question

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What services does Fidante offer?",
    "website_url": "https://www.fidante.com",
    "top_k": 5
  }'
```

Response:
```json
{
  "answer": "Fidante offers investment management services...",
  "sources": [
    {
      "page_url": "https://www.fidante.com/about",
      "content_snippet": "...",
      "relevance_score": 0.87
    }
  ],
  "question": "What services does Fidante offer?"
}
```

### 4. Crawl Another Website

The solution is fully generic. Simply provide a different URL:

```bash
curl -X POST http://localhost:8000/api/v1/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.pimco.com/", "max_pages": 100}'
```

## Configuration

All settings are configurable via environment variables or the `.env` file:

| Variable                  | Default                      | Description                      |
|--------------------------|------------------------------|----------------------------------|
| `OPENAI_API_KEY`         | *(required)*                 | Your OpenAI API key              |
| `OPENAI_MODEL`           | `gpt-4o-mini`                | LLM model for Q&A               |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small`     | Embedding model                  |
| `CRAWL_MAX_PAGES`        | `100`                        | Max pages per crawl              |
| `CRAWL_MAX_DEPTH`        | `3`                          | Max link depth                   |
| `CRAWL_DELAY_SECONDS`    | `1.0`                        | Polite delay between requests    |
| `CRAWL_RESPECT_ROBOTS_TXT`| `true`                      | Honour robots.txt                |
| `CHUNK_SIZE`             | `1024`                       | Text chunk size for indexing     |
| `CHUNK_OVERLAP`          | `200`                        | Overlap between chunks           |
| `CHROMA_PERSIST_DIR`     | `~/.webcrawler/chroma_db`    | ChromaDB storage path            |
| `DEBUG`                  | `false`                      | Enable debug logging             |

## How It Works

1. **Crawl** - Selenium in headless mode visits the target URL, renders JavaScript, and BeautifulSoup extracts clean text content. The crawler follows same-domain links up to the configured depth/page limits while respecting `robots.txt`.

2. **Index** - Crawled pages are converted to LlamaIndex `Document` objects, split into chunks using `SentenceSplitter`, embedded via OpenAI embeddings, and stored in ChromaDB.

3. **Query** - When you ask a question, LlamaIndex retrieves the most relevant chunks from ChromaDB, sends them as context to the OpenAI LLM, and returns a synthesised answer with source references.

## License

MIT
