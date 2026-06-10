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
- **Dependency Injection**: FastAPI's `Depends()` for loose coupling
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
| `GET` | `/health` | Health check | ❌ |
| `POST` | `/api/ingest` | Upload & process PDF (max 20 pages) | ✅ |
| `POST` | `/api/chat` | Ask questions (streaming SSE response) | ✅ |
| `GET` | `/api/documents/count` | Count stored document chunks | ✅ |
| `DELETE` | `/api/documents` | Cleanup documents: `?filename=...` or `?all=true` | ✅ |

### Example: Cleanup Documents

```bash
# Delete all chunks from one file
curl -X DELETE "http://localhost:8000/api/documents?filename=document.pdf" \
  -H "X-API-Key: your_secret_api_key"

# Wipe the entire collection
curl -X DELETE "http://localhost:8000/api/documents?all=true" \
  -H "X-API-Key: your_secret_api_key"
```

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
│   │   ├── dependencies.py     # Dependency injection
│   │   ├── middleware.py       # Error handling middleware
│   │   └── v1/
│   │       ├── router.py       # Route aggregation
│   │       ├── health.py       # Health endpoint
│   │       ├── ingest.py       # PDF ingestion
│   │       └── chat.py         # Chat endpoint
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
├── tests/                      # Functional test suite (pytest)
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

## 🧪 Testing

The suite under `tests/` runs **functional tests against the live services**
configured in your `.env` (MongoDB Atlas + the chat/embedding endpoint). It is
safe to run repeatedly:

- Every test document uses a `__pytest__` filename prefix and is auto-deleted
  before and after each test.
- The destructive `?all=true` test **skips itself** if the collection holds any
  real (non-test) documents, so it never wipes your data.
- The RAG test creates the vector index (with the live embedding dimension) if
  it is missing, then waits until it is queryable.

```bash
# Install test dependencies (includes runtime deps)
pip install -r requirements-dev.txt

# Run the whole suite
pytest

# Run a subset
pytest tests/test_documents.py
pytest -k rag
```

| Test file | Covers |
|-----------|--------|
| `test_health.py` | `/health` |
| `test_llm.py` | Live chat + embedding provider connectivity |
| `test_documents.py` | Ingest, count, and cleanup endpoints (incl. auth/guards) |
| `test_rag.py` | End-to-end RAG: ingest → vector search → grounded answer |

> Requires a populated `.env` and network access. Without them the app cannot
> start and the suite will error on collection.

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
