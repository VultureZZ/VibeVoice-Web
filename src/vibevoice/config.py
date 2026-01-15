"""
Configuration management for VibeVoice API.

Loads configuration from environment variables or .env file.
"""
import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv

    # Load environment variables from .env file if it exists
    load_dotenv()
except Exception:
    # Keep imports optional for minimal environments; production should install python-dotenv.
    pass

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


class Config:
    """Application configuration."""

    PROJECT_ROOT = PROJECT_ROOT

    # API Key (optional - if not set, any key is accepted)
    API_KEY: Optional[str] = os.getenv("API_KEY", None)

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))

    # Paths
    MODEL_PATH: Path = Path(os.getenv("MODEL_PATH", "models/VibeVoice-1.5B"))
    CUSTOM_VOICES_DIR: Path = Path(os.getenv("CUSTOM_VOICES_DIR", "custom_voices"))
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))
    PODCASTS_DIR: Path = Path(os.getenv("PODCASTS_DIR", "podcasts"))
    VIBEVOICE_REPO_DIR: Path = Path(os.getenv("VIBEVOICE_REPO_DIR", "VibeVoice"))

    # Realtime TTS (VibeVoice-Realtime-0.5B demo server)
    # These settings are used by the backend to launch/manage a local realtime model server
    # and bridge WebSocket audio chunks to the frontend.
    REALTIME_VIBEVOICE_REPO_DIR: Path = Path(
        os.getenv("REALTIME_VIBEVOICE_REPO_DIR", os.getenv("VIBEVOICE_REPO_DIR", "VibeVoice"))
    )
    REALTIME_MODEL_ID: str = os.getenv(
        "REALTIME_MODEL_ID", "microsoft/VibeVoice-Realtime-0.5B"
    )
    REALTIME_DEVICE: str = os.getenv("REALTIME_DEVICE", "cuda")
    REALTIME_HOST: str = os.getenv("REALTIME_HOST", "127.0.0.1")
    # Default chosen to avoid common dev servers on 3000.
    REALTIME_PORT: int = int(os.getenv("REALTIME_PORT", "6767"))
    REALTIME_STARTUP_TIMEOUT_SECONDS: float = float(
        os.getenv("REALTIME_STARTUP_TIMEOUT_SECONDS", "60")
    )
    # Optional explicit command for starting the realtime server. If set, overrides defaults.
    # Example:
    #   REALTIME_SERVER_COMMAND="python /path/to/VibeVoice/demo/vibevoice_realtime_demo.py --port 3000 --model_path microsoft/VibeVoice-Realtime-0.5B"
    REALTIME_SERVER_COMMAND: Optional[str] = os.getenv("REALTIME_SERVER_COMMAND", None)

    # Server
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # Ollama configuration
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")

    def __init__(self):
        """Initialize configuration and ensure directories exist."""
        # Convert relative paths to absolute paths relative to project root
        if not self.MODEL_PATH.is_absolute():
            self.MODEL_PATH = PROJECT_ROOT / self.MODEL_PATH
        if not self.CUSTOM_VOICES_DIR.is_absolute():
            self.CUSTOM_VOICES_DIR = PROJECT_ROOT / self.CUSTOM_VOICES_DIR
        if not self.OUTPUT_DIR.is_absolute():
            self.OUTPUT_DIR = PROJECT_ROOT / self.OUTPUT_DIR
        if not self.PODCASTS_DIR.is_absolute():
            self.PODCASTS_DIR = PROJECT_ROOT / self.PODCASTS_DIR
        if not self.VIBEVOICE_REPO_DIR.is_absolute():
            self.VIBEVOICE_REPO_DIR = PROJECT_ROOT / self.VIBEVOICE_REPO_DIR
        if not self.REALTIME_VIBEVOICE_REPO_DIR.is_absolute():
            self.REALTIME_VIBEVOICE_REPO_DIR = PROJECT_ROOT / self.REALTIME_VIBEVOICE_REPO_DIR

        # If the user didn't explicitly set REALTIME_VIBEVOICE_REPO_DIR, try a sensible default:
        # prefer a microsoft/VibeVoice checkout if present (it contains the realtime demo server).
        realtime_repo_env = os.getenv("REALTIME_VIBEVOICE_REPO_DIR")
        if not realtime_repo_env:
            candidate = PROJECT_ROOT / "VibeVoice-Microsoft"
            expected_demo = candidate / "demo" / "vibevoice_realtime_demo.py"
            current_expected_demo = (
                self.REALTIME_VIBEVOICE_REPO_DIR / "demo" / "vibevoice_realtime_demo.py"
            )
            if not current_expected_demo.exists() and expected_demo.exists():
                self.REALTIME_VIBEVOICE_REPO_DIR = candidate

        # Ensure directories exist
        self.CUSTOM_VOICES_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.PODCASTS_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def requires_api_key(self) -> bool:
        """Check if API key validation is required."""
        return self.API_KEY is not None and self.API_KEY != ""

    def validate_api_key(self, provided_key: Optional[str]) -> bool:
        """
        Validate provided API key.

        Args:
            provided_key: The API key provided by the client

        Returns:
            True if key is valid (or no key required), False otherwise
        """
        if not self.requires_api_key:
            # No API key required, accept any key or no key
            return True
        # API key required, validate against configured key
        return provided_key == self.API_KEY


# Global configuration instance
config = Config()
