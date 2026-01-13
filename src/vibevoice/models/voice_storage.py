"""
Voice metadata storage using JSON files.

Thread-safe operations for managing voice metadata.
"""
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..config import config


class VoiceStorage:
    """Thread-safe voice metadata storage."""

    def __init__(self, storage_file: Optional[Path] = None):
        """
        Initialize voice storage.

        Args:
            storage_file: Path to JSON storage file (defaults to custom_voices_dir/voice_metadata.json)
        """
        if storage_file is None:
            storage_file = config.CUSTOM_VOICES_DIR / "voice_metadata.json"
        self.storage_file = storage_file
        self.lock = threading.Lock()
        self._ensure_storage_file()

    def _ensure_storage_file(self) -> None:
        """Ensure storage file exists with proper structure."""
        if not self.storage_file.exists():
            with self.lock:
                self.storage_file.parent.mkdir(parents=True, exist_ok=True)
                initial_data = {"voices": {}}
                self.storage_file.write_text(json.dumps(initial_data, indent=2))

    def _load(self) -> Dict:
        """Load metadata from storage file."""
        try:
            if self.storage_file.exists():
                content = self.storage_file.read_text()
                return json.loads(content)
            return {"voices": {}}
        except (json.JSONDecodeError, IOError):
            return {"voices": {}}

    def _save(self, data: Dict) -> None:
        """Save metadata to storage file."""
        with self.lock:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            self.storage_file.write_text(json.dumps(data, indent=2))

    def add_voice(
        self,
        voice_id: str,
        name: str,
        description: Optional[str] = None,
        audio_files: Optional[List[str]] = None,
    ) -> None:
        """
        Add a new voice to storage.

        Args:
            voice_id: Unique voice identifier
            name: Voice name
            description: Voice description
            audio_files: List of audio file names
        """
        data = self._load()
        data["voices"][voice_id] = {
            "name": name,
            "description": description or "",
            "type": "custom",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "audio_files": audio_files or [],
        }
        self._save(data)

    def get_voice(self, voice_id: str) -> Optional[Dict]:
        """
        Get voice metadata by ID.

        Args:
            voice_id: Voice identifier

        Returns:
            Voice metadata dict or None if not found
        """
        data = self._load()
        voice = data["voices"].get(voice_id)
        if voice:
            voice["id"] = voice_id
        return voice

    def list_voices(self) -> List[Dict]:
        """
        List all custom voices.

        Returns:
            List of voice metadata dicts
        """
        data = self._load()
        voices = []
        for voice_id, voice_data in data["voices"].items():
            voice_data["id"] = voice_id
            voices.append(voice_data)
        return voices

    def delete_voice(self, voice_id: str) -> bool:
        """
        Delete a voice from storage.

        Args:
            voice_id: Voice identifier

        Returns:
            True if deleted, False if not found
        """
        data = self._load()
        if voice_id in data["voices"]:
            del data["voices"][voice_id]
            self._save(data)
            return True
        return False

    def voice_exists(self, voice_id: str) -> bool:
        """
        Check if a voice exists.

        Args:
            voice_id: Voice identifier

        Returns:
            True if voice exists, False otherwise
        """
        data = self._load()
        return voice_id in data["voices"]

    def name_exists(self, name: str, exclude_voice_id: Optional[str] = None) -> bool:
        """
        Check if a voice name already exists.

        Args:
            name: Voice name to check
            exclude_voice_id: Voice ID to exclude from check (for updates)

        Returns:
            True if name exists, False otherwise
        """
        data = self._load()
        for voice_id, voice_data in data["voices"].items():
            if exclude_voice_id and voice_id == exclude_voice_id:
                continue
            if voice_data["name"].lower() == name.lower():
                return True
        return False


# Global storage instance
voice_storage = VoiceStorage()
