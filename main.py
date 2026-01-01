import os
import io
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
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

if not MONGO_URI or not GEMINI_API_KEY:
    raise ValueError("MONGO_URI and GEMINI_API_KEY must be set in .env file")

# Initialize Clients
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
collection = db[COLLECTION_NAME]

client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="Breaking B.A.D. API")

class ChatRequest(BaseModel):
    question: str

@app.get("/health")
async def health_check():
    return {"status": "awake"}

@app.post("/api/ingest")
async def ingest_pdf(file: UploadFile = File(...)):
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
async def chat(request: ChatRequest):
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
            system_prompt = "You are Breaking B.A.D. Answer based ONLY on the context provided. If you don't know the answer based on the context, say you don't know."
            prompt = f"{system_prompt}\n\nContext:\n{context}\n\nQuestion: {request.question}"
            
            # Send sources first
            yield f"data: {json.dumps({'sources': sources})}\n\n"
            
            config = types.GenerateContentConfig(
                system_instruction=system_prompt
            )
            
            # Use generate_content_stream for streaming
            # Note: For thinking models, thoughts are in the 'parts'
            # We use the thinking model specifically if needed
            model_id = 'gemini-2.0-flash'
            
            responses = client.models.generate_content_stream(
                model=model_id,
                contents=request.question,
                config=types.GenerateContentConfig(
                    system_instruction=f"Context:\n{context}"
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
