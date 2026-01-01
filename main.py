import os
import io
import json
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Security
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from pypdf import PdfReader
from pymongo import MongoClient
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DB_NAME = os.getenv("DB_NAME", "rag_app")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "documents")
API_KEY = os.getenv("API_KEY")

if not MONGO_URI or not GEMINI_API_KEY:
    raise ValueError("MONGO_URI and GEMINI_API_KEY must be set in .env file")

if not API_KEY:
    raise ValueError("API_KEY must be set in .env file for security")

# Initialize Clients
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
collection = db[COLLECTION_NAME]

client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="Breaking B.A.D. API")

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key Security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key is None or api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key

class HistoryItem(BaseModel):
    role: str # 'user' or 'model'
    parts: List[dict] # [{'text': '...'}]

class ChatRequest(BaseModel):
    question: str
    history: Optional[List[HistoryItem]] = []

@app.get("/health")
async def health_check():
    return {"status": "awake"}

@app.post("/api/ingest")
async def ingest_pdf(file: UploadFile = File(...), _: str = Depends(verify_api_key)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        content = await file.read()
        pdf_reader = PdfReader(io.BytesIO(content))
        
        chunks = []
        # Constraint: Process max 20 pages
        num_pages = min(len(pdf_reader.pages), 20)
        
        for i in range(num_pages):
            page = pdf_reader.pages[i]
            text = page.extract_text()
            if not text.strip():
                continue
                
            # Generate embedding
            embedding_response = client.models.embed_content(
                model="text-embedding-004",
                contents=text,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            embedding = embedding_response.embeddings[0].values
            
            chunks.append({
                "text": text,
                "embedding": embedding,
                "filename": file.filename,
                "chunk_id": i
            })
            
        if chunks:
            collection.insert_many(chunks)
            
        return {"message": "Success", "chunks_stored": len(chunks)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest, _: str = Depends(verify_api_key)):
    try:
        # 1. Embed the question
        query_embedding_response = client.models.embed_content(
            model="text-embedding-004",
            contents=request.question,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
        )
        query_embedding = query_embedding_response.embeddings[0].values
        
        # 2. Perform Vector Search (Requires Atlas Vector Search Index)
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index", # This must match the index name in Atlas
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": 50,
                    "limit": 5
                }
            }
        ]
        
        results = list(collection.aggregate(pipeline))
        context = "\n\n".join([doc["text"] for doc in results]) if results else "No relevant context found."
        sources = [doc["filename"] for doc in results] if results else []

        # 3. Streaming Generator
        def generate_stream():
            system_prompt = "You are Breaking B.A.D. (Bot Answering Dialogue). Your primary source of truth is the provided 'Context'. If the answer is in the context, use it. If the context doesn't contain the answer, you may answer using your general knowledge, but maintain your persona and clarify if needed that the info isn't from the documents. Always be helpful and keep your persona consistent."
            
            # Send sources first
            yield f"data: {json.dumps({'sources': sources})}\n\n"
            
            # Prepare contents for Gemini
            contents = []
            
            # Add history if available
            if request.history:
                for item in request.history:
                    contents.append(types.Content(
                        role=item.role,
                        parts=[types.Part(text=p['text']) for p in item.parts]
                    ))
            
            # Add current question
            contents.append(types.Content(
                role="user",
                parts=[types.Part(text=request.question)]
            ))
            
            model_id = 'gemini-2.0-flash'
            
            responses = client.models.generate_content_stream(
                model=model_id,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=f"{system_prompt}\n\nContext:\n{context}"
                )
            )
            
            for response in responses:
                if response.candidates:
                    for part in response.candidates[0].content.parts:
                        data = {}
                        if part.thought:
                            data["thought"] = part.thought
                        if part.text:
                            data["answer"] = part.text
                        
                        if data:
                            yield f"data: {json.dumps(data)}\n\n"
        
        return StreamingResponse(generate_stream(), media_type="text/event-stream")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
