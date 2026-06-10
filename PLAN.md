# Project Spec: Breaking B.A.D. (Backend)

**App Name:** Breaking B.A.D. (Bot Answering Dialogue)
**Tagline:** "Breaking down files. Building up answers."
**Type:** RAG (Retrieval Augmented Generation) Chatbot API
**Hosting:** Render (Web Service)

## 1. Tech Stack
* **Language:** Python 3.10+
* **Framework:** FastAPI
* **Server:** Uvicorn (Development) / Gunicorn (Production)
* **Database:** MongoDB Atlas (for Vector Storage)
* **AI Provider:** Pluggable per role (chat & embedding chosen independently)
    * **Google Gemini** via `google-genai` SDK, **or**
    * any **OpenAI-compatible** endpoint via `openai` SDK (OpenAI, vLLM, Ollama, LM Studio, Together, Groq, etc.)
    * **LLM (example):** `gemini-2.5-flash-lite` / `gpt-4o-mini` / `Qwen2.5-72B-Instruct`
    * **Embeddings (example):** `gemini-embedding-001` / `text-embedding-3-small`
* **PDF Processing:** `pypdf`

## 2. Directory Structure
* `main.py` (The FastAPI entry point)
* `requirements.txt` (Dependencies)
* `.env` (Local environment variables)

## 3. Environment Variables
The application requires the following environment variables:
* `MONGO_URI`: Connection string for MongoDB Atlas.
* `API_KEY`: Secret key for authenticating API requests.
* `CHAT_PROVIDER` / `EMBEDDING_PROVIDER`: `gemini` or `openai` (default `gemini`).
* `GEMINI_API_KEY`: API Key from Google AI Studio (required if any provider is `gemini`).
* `OPENAI_API_KEY` / `OPENAI_BASE_URL`: credentials + endpoint for OpenAI-compatible providers.
* `CHAT_MODEL` / `EMBEDDING_MODEL`: model names matching the selected providers.
* `DB_NAME`: `rag_app`
* `COLLECTION_NAME`: `documents`

## 4. Database Schema & Index
The MongoDB collection `documents` in database `rag_app` must have a Vector Search Index configured in Atlas using the "JSON Editor":

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

**Document Schema:**
{
  "text": "The raw text content...",
  "embedding": [0.01, -0.2, ...],
  "filename": "my_report.pdf",
  "chunk_id": 0
}

## 5. API Endpoints

### A. Health Check (Keep-Alive)
* **Method:** `GET`
* **Path:** `/health`
* **Description:** Returns `{"status": "awake"}` to prevent Render cold starts.

### B. Ingest PDF
* **Method:** `POST`
* **Path:** `/api/ingest`
* **Input:** `file` (UploadFile, PDF)
* **Logic:**
    1. Read PDF with `pypdf`.
    2. Extract text page by page (1 page = 1 chunk).
    3. Generate embeddings for each chunk using `text-embedding-004`.
    4. Insert documents into MongoDB.
    5. **Constraint:** Process max 20 pages per file for MVP safety.
* **Response:** JSON confirming number of chunks stored.

### C. Chat
* **Method:** `POST`
* **Path:** `/api/chat`
* **Input Body:** `{ "question": "User query here" }`
* **Logic:**
    1. Embed the `question`.
    2. Perform `$vectorSearch` on MongoDB to find top 5 matches.
    3. Concatenate text from matches as `Context`.
    4. Send `Context` + `Question` to the configured chat model (`CHAT_PROVIDER`).
    5. **System Prompt:** "You are Breaking B.A.D. Answer based ONLY on the context."

## 6. Implementation Details
**`requirements.txt` content:**
fastapi
uvicorn
gunicorn
python-multipart
pymongo
google-genai
openai
pypdf
python-dotenv

## 7. Render Deployment
* Ensure `main.py` uses `os.environ.get("PORT", 8000)` and binds to `0.0.0.0`.