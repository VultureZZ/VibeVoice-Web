"""
FastAPI application entry point for VibeVoice API.
"""
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import config
from .middleware.auth import APIKeyAuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .routes import speech, voices, podcasts
from .routes import realtime_speech
from .services.realtime_process import realtime_process_manager

# Import podcast router using file-based import
from pathlib import Path
import importlib.util
_podcast_file = Path(__file__).parent / "routes" / "podcast.py"
_spec = importlib.util.spec_from_file_location("vibevoice.routes.podcast", _podcast_file)
_podcast_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_podcast_module)
podcast_router = _podcast_module.router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

# Set specific loggers
logging.getLogger("vibevoice").setLevel(logging.INFO)
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="VibeVoice API",
    description="REST API for VibeVoice text-to-speech generation",
    version="1.0.0",
)

logger.info("=" * 80)
logger.info("VibeVoice API Starting")
logger.info("=" * 80)
logger.info("Configuration:")
logger.info("  TTS backend: %s", config.TTS_BACKEND)
if config.TTS_BACKEND.strip().lower() == "vibevoice":
    logger.info("  Model path: %s", config.MODEL_PATH)
else:
    logger.info("  Qwen3 CustomVoice model: %s", getattr(config, "QWEN_TTS_CUSTOM_VOICE_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"))
logger.info("  Output directory: %s", config.OUTPUT_DIR)
logger.info("  Custom voices directory: %s", config.CUSTOM_VOICES_DIR)
logger.info("  Rate limit: %s requests/minute", config.RATE_LIMIT_PER_MINUTE)
logger.info("  API key required: %s", config.requires_api_key)
logger.info("Realtime configuration:")
logger.info(f"  Realtime host: {config.REALTIME_HOST}")
logger.info(f"  Realtime port: {config.REALTIME_PORT}")
logger.info(f"  Realtime model: {config.REALTIME_MODEL_ID}")
logger.info(f"  Realtime device: {config.REALTIME_DEVICE}")
logger.info(f"  Realtime repo dir: {config.REALTIME_VIBEVOICE_REPO_DIR}")
logger.info("=" * 80)

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
app.include_router(realtime_speech.router)
app.include_router(voices.router)
app.include_router(podcast_router)
app.include_router(podcasts.router)


@app.on_event("shutdown")
async def _shutdown() -> None:
    # Best-effort shutdown of the realtime subprocess (if we started it).
    realtime_process_manager.stop()


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
