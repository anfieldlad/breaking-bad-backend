# Breaking B.A.D. 🧪

**Bot Answering Dialogue** — *"Breaking down files. Building up answers."*

A RAG (Retrieval Augmented Generation) chatbot API that ingests PDF documents and answers questions based on their content using publicly available Gemini API.

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
| AI Provider | Google Gemini API |
| LLM | `gemini-2.0-flash` |
| Embeddings | `text-embedding-004` |
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

Create a `.env` file:

```env
MONGO_URI=your_mongodb_atlas_connection_string
GEMINI_API_KEY=your_gemini_api_key
DB_NAME=rag_app
COLLECTION_NAME=documents
API_KEY=your_secret_api_key
```

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
│       ├── embedding_service.py    # Gemini embeddings
│       ├── pdf_service.py          # PDF processing
│       ├── chat_service.py         # RAG orchestration
│       └── ingestion_service.py    # Ingestion pipeline
├── main.py                     # Entry point
├── requirements.txt            # Dependencies (pinned)
├── .env.example
└── README.md
```

## 🔧 Configuration

All configuration is managed via environment variables with sensible defaults:

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB Atlas connection string | Required |
| `GEMINI_API_KEY` | Google AI API key | Required |
| `API_KEY` | API authentication key | Required |
| `DB_NAME` | Database name | `rag_app` |
| `COLLECTION_NAME` | Collection name | `documents` |
| `MAX_PAGES_PER_PDF` | Max pages to process | `20` |

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
