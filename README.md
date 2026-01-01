# Breaking B.A.D. 🧪

**Bot Answering Dialogue** — *"Breaking down files. Building up answers."*

A RAG (Retrieval Augmented Generation) chatbot API that ingests PDF documents and answers questions based on their content using Google Gemini AI.

## Tech Stack

- **Framework:** FastAPI
- **Database:** MongoDB Atlas (Vector Storage)
- **AI:** Google Gemini API
  - LLM: `gemini-2.0-flash`
  - Embeddings: `text-embedding-004`
- **PDF Processing:** pypdf

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/anfieldlad/breaking-bad-backend.git
cd breaking-bad-backend
python -m venv .venv
.venv\Scripts\activate  # Windows
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

Create a Vector Search Index named `vector_index` on your collection using:

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
uvicorn main:app --reload
```

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/health` | Health check | ❌ |
| `POST` | `/api/ingest` | Upload & process PDF (max 20 pages) | ✅ |
| `POST` | `/api/chat` | Ask questions (streaming SSE response) | ✅ |

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

## Related

- **Frontend UI:** [breaking-bad-ui](https://github.com/anfieldlad/breaking-bad-ui)

## License

MIT
