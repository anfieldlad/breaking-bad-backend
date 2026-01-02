"""
Breaking B.A.D. Backend - Application Entry Point

This module serves as the entry point for running the application.
It imports the FastAPI app from the app package and runs it with uvicorn.

Usage:
    python main.py
    
Or with uvicorn directly:
    uvicorn app.main:app --reload
"""

import os

import uvicorn

from app.main import app  # noqa: F401 - imported for uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.environ.get("RELOAD", "false").lower() == "true",
    )
