"""
FastAPI application entry point for VibeVoice API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import config
from .middleware.auth import APIKeyAuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .routes import speech, voices

# Create FastAPI app
app = FastAPI(
    title="VibeVoice API",
    description="REST API for VibeVoice text-to-speech generation",
    version="1.0.0",
)

# Add CORS middleware (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware
app.add_middleware(APIKeyAuthMiddleware)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Register routes
app.include_router(speech.router)
app.include_router(voices.router)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "VibeVoice API",
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    """
    Root endpoint.

    Returns:
        API information
    """
    return {
        "message": "VibeVoice API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Add src directory to Python path if running directly
    project_root = Path(__file__).parent.parent.parent
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    import uvicorn

    uvicorn.run(
        "vibevoice.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
    )
