# Breaking B.A.D. 🧪

**Bot Answering Dialogue** — *"Breaking down files. Building up answers."*

A RAG (Retrieval Augmented Generation) chatbot API that ingests PDF documents and answers questions based on their content. The LLM backend is pluggable — both chat and embeddings can independently use **Google Gemini** or any **OpenAI-compatible** endpoint (OpenAI, vLLM, Ollama, LM Studio, Together, Groq, etc.).

## 🏗️ Architecture

This project follows **Clean Architecture** with **SOLID principles**:

```
app/
├── core/           # Configuration, logging, exceptions
├── models/         # Domain models and Pydantic schemas
├── repositories/   # Data access layer (MongoDB)
├── services/       # Business logic layer
└── api/            # HTTP layer (routes, middleware, DI)
```

### Key Design Decisions

- **Single Responsibility**: Each module handles one concern
- **Dependency Injection**: services are built once at startup (`app/api/container.py`) and injected with `Depends()`
- **Observability**: every request gets an `X-Request-ID` that appears in all its log lines; `LOG_FORMAT=json` for structured logs
- **Centralized errors**: services raise typed exceptions; `app/api/errors.py` maps them to `{"detail": ...}` responses without leaking internals
- **Repository Pattern**: Abstract data access for testability
- **Service Layer**: Business logic isolated from HTTP concerns
- **Type Safety**: Pydantic for validation, type hints throughout

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Database | MongoDB Atlas (Vector Storage) |
| AI Provider | Google Gemini **or** any OpenAI-compatible endpoint (configurable per role) |
| LLM | e.g. `gemini-2.5-flash-lite` / `gpt-4o-mini` / `Qwen2.5-72B-Instruct` |
| Embeddings | e.g. `gemini-embedding-001` / `text-embedding-3-small` |
| PDF Processing | pypdf |

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/anfieldlad/breaking-bad-backend.git
cd breaking-bad-backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file (see [.env.example](./.env.example) for all options):

```env
MONGO_URI=your_mongodb_atlas_connection_string
API_KEY=your_secret_api_key
DB_NAME=rag_app
COLLECTION_NAME=documents

# Provider selection (each can be "gemini" or "openai")
CHAT_PROVIDER=gemini
EMBEDDING_PROVIDER=gemini

# Required when a provider above is "gemini"
GEMINI_API_KEY=your_gemini_api_key

# Required when a provider above is "openai" (any OpenAI-compatible endpoint)
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1   # e.g. http://localhost:11434/v1 for Ollama

# Models — must match the selected provider
CHAT_MODEL=gemini-2.5-flash-lite
EMBEDDING_MODEL=gemini-embedding-001
```

> **Example — Qwen for chat, Gemini for embeddings** (no vector reindex needed):
> set `CHAT_PROVIDER=openai`, `OPENAI_BASE_URL` to your Qwen endpoint, `CHAT_MODEL` to your model name, and keep `EMBEDDING_PROVIDER=gemini`.

### 3. MongoDB Atlas Vector Index

Create a Vector Search Index named `vector_index` on your collection:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 768,
      "similarity": "cosine"
    }
  ]
}
```

> ⚠️ **`numDimensions` must match your embedding model's output size** (e.g. `text-embedding-3-small` = 1536, `gemini-embedding-001` = 3072). If you change the embedding model/provider, recreate this index with the new dimension and **re-ingest** all documents. Switching only the chat provider does **not** affect the index.

### 4. Run

```bash
# Development (with reload)
uvicorn app.main:app --reload

# Production
python main.py
```

## 📡 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/health` | Liveness (process is up; keep-alive) | ❌ |
| `GET` | `/health/ready` | Readiness (MongoDB reachable), `503` otherwise | ❌ |
| `POST` | `/api/ingest` | Upload & process PDF (max 20 pages, 10 MB); re-uploading a filename replaces it | ✅ |
| `POST` | `/api/chat` | Ask questions (streaming SSE response) | ✅ |
| `GET` | `/api/documents/count` | Count stored document chunks | ✅ |
| `DELETE` | `/api/documents` | Cleanup documents: `?filename=...` or `?all=true` | ✅ |

### Example: Cleanup Documents

```bash
# Delete all chunks from one file
curl -X DELETE "http://localhost:8000/api/documents?filename=document.pdf" \
  -H "X-API-Key: your_secret_api_key" \
  -H "X-Cleanup-Password: your_cleanup_password"

# Wipe the entire collection
curl -X DELETE "http://localhost:8000/api/documents?all=true" \
  -H "X-API-Key: your_secret_api_key" \
  -H "X-Cleanup-Password: your_cleanup_password"
```

> Cleanup is **disabled** (always `403`) unless `CLEANUP_PASSWORD` is set.

### Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Example: Ingest PDF

```bash
curl -X POST "http://localhost:8000/api/ingest" \
  -H "X-API-Key: your_secret_api_key" \
  -F "file=@document.pdf"
```

### Example: Chat

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "X-API-Key: your_secret_api_key" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?"}'
```

### Example: Multi-turn Chat

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "X-API-Key: your_secret_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Can you explain more?",
    "history": [
      {"role": "user", "parts": [{"text": "What is the main topic?"}]},
      {"role": "model", "parts": [{"text": "The document discusses..."}]}
    ]
  }'
```

## 📁 Project Structure

```
breaking-bad-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app factory
│   ├── core/
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── logging.py          # Structured logging
│   │   └── exceptions.py       # Custom exceptions
│   ├── api/
│   │   ├── container.py        # Builds long-lived services at startup
│   │   ├── dependencies.py     # Dependency injection
│   │   ├── errors.py           # Exception → HTTP response mapping
│   │   ├── middleware.py       # Request ID + access log (pure ASGI)
│   │   └── v1/
│   │       ├── router.py       # Route aggregation
│   │       ├── health.py       # Health endpoint
│   │       ├── ingest.py       # PDF ingestion
│   │       ├── chat.py         # Chat endpoint
│   │       └── documents.py    # Count / cleanup endpoints
│   ├── models/
│   │   ├── document.py         # Document domain model
│   │   └── schemas.py          # Pydantic schemas
│   ├── repositories/
│   │   ├── base.py             # Abstract repository
│   │   └── document_repository.py  # MongoDB implementation
│   └── services/
│       ├── providers/              # Pluggable LLM backends (Gemini / OpenAI-compatible)
│       ├── embedding_service.py    # Embedding generation
│       ├── pdf_service.py          # PDF processing
│       ├── chat_service.py         # RAG orchestration
│       └── ingestion_service.py    # Ingestion pipeline
├── tests/
│   ├── unit/                   # Offline tests with in-memory fakes (default)
│   └── integration/            # Live tests against Atlas + LLM (opt-in)
├── main.py                     # Entry point
├── requirements.txt            # Dependencies (pinned)
├── requirements-dev.txt        # Test/dev dependencies
├── pytest.ini
├── .env.example
└── README.md
```

## 🔧 Configuration

All configuration is managed via environment variables with sensible defaults:

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB Atlas connection string | Required |
| `API_KEY` | API authentication key | Required |
| `CHAT_PROVIDER` | Chat backend: `gemini` or `openai` | `gemini` |
| `EMBEDDING_PROVIDER` | Embedding backend: `gemini` or `openai` | `gemini` |
| `GEMINI_API_KEY` | Google AI API key (required if any provider is `gemini`) | `""` |
| `OPENAI_API_KEY` | API key (required if any provider is `openai`) | `""` |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint URL | `https://api.openai.com/v1` |
| `CHAT_MODEL` | Chat model name (must match provider) | `gemini-2.5-flash-lite` |
| `EMBEDDING_MODEL` | Embedding model name (must match provider) | `gemini-embedding-001` |
| `DB_NAME` | Database name | `rag_app` |
| `COLLECTION_NAME` | Collection name | `documents` |
| `MAX_PAGES_PER_PDF` | Max pages to process | `20` |
| `MAX_UPLOAD_MB` | Max PDF upload size (larger uploads get `413`) | `10` |
| `CORS_ORIGINS` | Comma-separated browser origins allowed by CORS; empty disables CORS | `""` |
| `GEMINI_INCLUDE_THOUGHTS` | Stream Gemini reasoning as `thought` events (Gemini 2.5+) | `true` |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` | `INFO` |
| `LOG_FORMAT` | `text`, or `json` (one object per line, for log aggregation) | `text` |
| `MONGO_TIMEOUT_MS` | MongoDB server-selection timeout | `5000` |
| `CLEANUP_PASSWORD` | Password for `DELETE /api/documents`; empty disables cleanup | `""` |

## 🧪 Testing

```bash
# Install test dependencies (includes runtime deps)
pip install -r requirements-dev.txt

# Unit tests (default): offline, no .env or network needed
pytest

# Live functional tests against the services in your .env
pytest -m integration
```

**Unit tests** (`tests/unit/`) replace MongoDB and the LLM providers with
in-memory fakes via FastAPI dependency overrides, so they run anywhere,
including CI.

**Integration tests** (`tests/integration/`) hit MongoDB Atlas and the
configured chat/embedding endpoint. They are safe to run repeatedly:

- Every test document uses a `__pytest__` filename prefix and is auto-deleted
  before and after each test.
- The destructive `?all=true` test **skips itself** if the collection holds any
  real (non-test) documents, so it never wipes your data.
- Cleanup tests skip when `CLEANUP_PASSWORD` is not configured.
- The RAG test creates the vector index (with the live embedding dimension) if
  it is missing, then waits until it is queryable.

| Test file | Covers |
|-----------|--------|
| `unit/test_chat_api.py` | SSE stream shape, in-band `error` events, no leaked internals |
| `unit/test_documents_api.py` | Count + cleanup password gate |
| `unit/test_ingest_api.py` | Upload validation (type, magic bytes, size), re-ingest replaces |
| `unit/test_api_errors.py` | Auth, request limits, generic error responses |
| `unit/test_document_repository.py` | Mongo repository against a mocked driver |
| `unit/test_providers.py` | Gemini thought/answer parsing |
| `unit/test_app_startup.py` | Lifespan wiring, fail-fast config, CORS |
| `unit/test_observability.py` | Liveness/readiness, request IDs, JSON logs |
| `integration/test_health.py` | `/health` |
| `integration/test_llm.py` | Live chat + embedding provider connectivity |
| `integration/test_documents.py` | Ingest, count, and cleanup endpoints (incl. auth/guards) |
| `integration/test_rag.py` | End-to-end RAG: ingest → vector search → grounded answer |

## 🚢 Deployment

### Render

The app is configured for Render deployment:
- Uses `PORT` environment variable
- Binds to `0.0.0.0`
- Includes `gunicorn` for production

```bash
# Render start command
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 📚 Related

- **Frontend UI**: [breaking-bad-ui](https://github.com/anfieldlad/breaking-bad-ui)
- **UI Integration Guide**: [UI_INTEGRATION.md](./UI_INTEGRATION.md)

## 📄 License

MIT
