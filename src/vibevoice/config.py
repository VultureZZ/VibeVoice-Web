"""
Configuration management for VibeVoice API.

Loads configuration from environment variables or .env file.
"""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

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
    VIBEVOICE_REPO_DIR: Path = Path(os.getenv("VIBEVOICE_REPO_DIR", "VibeVoice"))

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
        if not self.VIBEVOICE_REPO_DIR.is_absolute():
            self.VIBEVOICE_REPO_DIR = PROJECT_ROOT / self.VIBEVOICE_REPO_DIR

        # Ensure directories exist
        self.CUSTOM_VOICES_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
