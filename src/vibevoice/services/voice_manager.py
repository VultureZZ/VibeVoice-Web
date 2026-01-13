"""
Voice management service.

Handles custom voice creation, listing, and deletion.
"""
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydub import AudioSegment

from ..config import config
from ..models.voice_storage import voice_storage

# Default voices that cannot be deleted
DEFAULT_VOICES = [
    "Alice",
    "Frank",
    "Mary",
    "Carter",
    "Maya",
    "en-Alice_woman",
    "en-Frank_man",
    "en-Mary_woman_bgm",
    "en-Carter_man",
    "en-Maya_woman",
]


class VoiceManager:
    """Service for managing voices."""

    def __init__(self):
        """Initialize voice manager."""
        self.custom_voices_dir = config.CUSTOM_VOICES_DIR
        self.vibevoice_repo_dir = config.VIBEVOICE_REPO_DIR
        self.default_voices_dir = self.vibevoice_repo_dir / "demo" / "voices"

    def is_default_voice(self, voice_name: str) -> bool:
        """
        Check if a voice is a default voice.

        Args:
            voice_name: Voice name to check

        Returns:
            True if default voice, False otherwise
        """
        return voice_name in DEFAULT_VOICES or voice_name.startswith("en-")

    def get_voice_id_from_name(self, name: str) -> str:
        """
        Convert voice name to a valid voice ID (sanitized).

        Args:
            name: Voice name

        Returns:
            Sanitized voice ID
        """
        # Replace spaces and special characters with underscores
        voice_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
        return voice_id.lower()

    def create_custom_voice(
        self,
        name: str,
        description: Optional[str],
        audio_files: List[Path],
    ) -> dict:
        """
        Create a custom voice from uploaded audio files.

        Args:
            name: Voice name
            description: Voice description
            audio_files: List of paths to uploaded audio files

        Returns:
            Dict with voice metadata

        Raises:
            ValueError: If name is invalid or files cannot be processed
        """
        # Validate name
        if not name or not name.strip():
            raise ValueError("Voice name cannot be empty")

        # Check if name is a default voice
        if self.is_default_voice(name):
            raise ValueError(f"Voice name '{name}' is reserved for default voices")

        # Generate voice ID
        voice_id = self.get_voice_id_from_name(name)

        # Check if voice ID already exists
        if voice_storage.voice_exists(voice_id):
            raise ValueError(f"Voice with name '{name}' already exists")

        # Check if name already exists (case-insensitive)
        if voice_storage.name_exists(name):
            raise ValueError(f"Voice with name '{name}' already exists")

        # Create voice directory structure
        voice_dir = self.custom_voices_dir / voice_id
        original_dir = voice_dir / "original"
        original_dir.mkdir(parents=True, exist_ok=True)

        # Save original files and combine them
        saved_files = []
        audio_segments = []

        try:
            for i, audio_file in enumerate(audio_files):
                # Validate file exists
                if not audio_file.exists():
                    raise ValueError(f"Audio file not found: {audio_file}")

                # Determine file extension
                ext = audio_file.suffix.lower()
                if ext not in [".wav", ".mp3", ".flac", ".m4a", ".ogg"]:
                    raise ValueError(f"Unsupported audio format: {ext}")

                # Save original file
                saved_filename = f"file_{i+1}{ext}"
                saved_path = original_dir / saved_filename
                shutil.copy2(audio_file, saved_path)
                saved_files.append(saved_filename)

                # Load audio segment
                try:
                    if ext == ".wav":
                        segment = AudioSegment.from_wav(str(saved_path))
                    elif ext == ".mp3":
                        segment = AudioSegment.from_mp3(str(saved_path))
                    elif ext == ".flac":
                        segment = AudioSegment.from_flac(str(saved_path))
                    elif ext == ".m4a":
                        segment = AudioSegment.from_file(str(saved_path), format="m4a")
                    elif ext == ".ogg":
                        segment = AudioSegment.from_ogg(str(saved_path))
                    else:
                        raise ValueError(f"Unsupported format: {ext}")

                    # Normalize sample rate to 24000 Hz (VibeVoice standard)
                    if segment.frame_rate != 24000:
                        segment = segment.set_frame_rate(24000)

                    # Convert to mono if stereo
                    if segment.channels > 1:
                        segment = segment.set_channels(1)

                    audio_segments.append(segment)
                except Exception as e:
                    raise ValueError(f"Failed to process audio file {audio_file}: {str(e)}")

            # Combine all audio segments
            if not audio_segments:
                raise ValueError("No valid audio files provided")

            combined_audio = sum(audio_segments)
            combined_path = voice_dir / "combined.wav"

            # Export combined audio as WAV
            combined_audio.export(str(combined_path), format="wav", parameters=["-ar", "24000"])

            # Save metadata
            voice_storage.add_voice(
                voice_id=voice_id,
                name=name,
                description=description,
                audio_files=saved_files,
            )

            # Return voice metadata
            voice_data = voice_storage.get_voice(voice_id)
            return voice_data

        except Exception as e:
            # Clean up on error
            if voice_dir.exists():
                shutil.rmtree(voice_dir)
            raise

    def delete_custom_voice(self, voice_id: str) -> bool:
        """
        Delete a custom voice.

        Args:
            voice_id: Voice identifier

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If trying to delete a default voice
        """
        # Get voice metadata
        voice_data = voice_storage.get_voice(voice_id)
        if not voice_data:
            return False

        # Check if it's a default voice
        if voice_data.get("type") == "default" or self.is_default_voice(voice_data.get("name", "")):
            raise ValueError("Cannot delete default voices")

        # Delete voice directory
        voice_dir = self.custom_voices_dir / voice_id
        if voice_dir.exists():
            shutil.rmtree(voice_dir)

        # Delete from storage
        return voice_storage.delete_voice(voice_id)

    def list_all_voices(self) -> List[dict]:
        """
        List all available voices (default + custom).

        Returns:
            List of voice metadata dicts
        """
        voices = []

        # Add default voices
        if self.default_voices_dir.exists():
            # Try to discover default voices from the voices directory
            for voice_file in self.default_voices_dir.glob("*.wav"):
                voice_name = voice_file.stem
                # Skip if already in our default list or if it's a system file
                if voice_name not in DEFAULT_VOICES and not voice_name.startswith("."):
                    DEFAULT_VOICES.append(voice_name)

        # Add hardcoded default voices
        for voice_name in DEFAULT_VOICES:
            voices.append({
                "id": voice_name,
                "name": voice_name,
                "description": f"Default VibeVoice voice: {voice_name}",
                "type": "default",
                "created_at": None,
                "audio_files": None,
            })

        # Add custom voices
        custom_voices = voice_storage.list_voices()
        for voice_data in custom_voices:
            # Parse created_at if it's a string
            if isinstance(voice_data.get("created_at"), str):
                try:
                    voice_data["created_at"] = datetime.fromisoformat(
                        voice_data["created_at"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass
            voices.append(voice_data)

        return voices

    def get_voice(self, voice_id: str) -> Optional[dict]:
        """
        Get voice metadata by ID.

        Args:
            voice_id: Voice identifier

        Returns:
            Voice metadata dict or None if not found
        """
        # Check custom voices first
        voice_data = voice_storage.get_voice(voice_id)
        if voice_data:
            return voice_data

        # Check default voices
        if self.is_default_voice(voice_id) or voice_id in DEFAULT_VOICES:
            return {
                "id": voice_id,
                "name": voice_id,
                "description": f"Default VibeVoice voice: {voice_id}",
                "type": "default",
                "created_at": None,
                "audio_files": None,
            }

        return None

    def get_voice_path(self, voice_id: str) -> Optional[Path]:
        """
        Get the path to a voice file.

        Args:
            voice_id: Voice identifier

        Returns:
            Path to voice file or None if not found
        """
        # Check custom voices
        voice_data = voice_storage.get_voice(voice_id)
        if voice_data:
            voice_dir = self.custom_voices_dir / voice_id
            combined_path = voice_dir / "combined.wav"
            if combined_path.exists():
                return combined_path

        # Check default voices
        if self.default_voices_dir.exists():
            # Try different naming conventions
            for pattern in [f"{voice_id}.wav", f"en-{voice_id}.wav", f"{voice_id}_*.wav"]:
                matches = list(self.default_voices_dir.glob(pattern))
                if matches:
                    return matches[0]

        return None


# Global voice manager instance
voice_manager = VoiceManager()
