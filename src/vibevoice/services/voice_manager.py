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
from .audio_validator import AudioValidator
from .voice_profiler import voice_profiler

# Default voices that cannot be deleted
# Mapping of short names to full voice file names
VOICE_NAME_MAPPING = {
    "Alice": "en-Alice_woman",
    "Frank": "en-Frank_man",
    "Mary": "en-Mary_woman_bgm",
    "Carter": "en-Carter_man",
    "Maya": "en-Maya_woman",
}

# Default voices list (both short and full names)
DEFAULT_VOICES = list(VOICE_NAME_MAPPING.keys()) + list(VOICE_NAME_MAPPING.values())


class VoiceManager:
    """Service for managing voices."""

    def __init__(self):
        """Initialize voice manager."""
        self.custom_voices_dir = config.CUSTOM_VOICES_DIR
        self.vibevoice_repo_dir = config.VIBEVOICE_REPO_DIR
        self.default_voices_dir = self.vibevoice_repo_dir / "demo" / "voices"
        self.audio_validator = AudioValidator()

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
        keywords: Optional[List[str]] = None,
        ollama_url: Optional[str] = None,
        ollama_model: Optional[str] = None,
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

            # Calculate combined duration
            combined_duration_seconds = len(combined_audio) / 1000.0

            # Validate audio files (analyze individual files and combined result)
            # Build list of saved file paths for validation
            saved_file_paths = [original_dir / filename for filename in saved_files]
            validation_feedback = self.audio_validator.validate_audio_files(
                audio_files=saved_file_paths,
                combined_duration_seconds=combined_duration_seconds,
            )

            # Export combined audio as WAV
            combined_audio.export(str(combined_path), format="wav", parameters=["-ar", "24000"])

            # Save metadata
            voice_storage.add_voice(
                voice_id=voice_id,
                name=name,
                description=description,
                audio_files=saved_files,
            )

            # Automatically profile the voice (non-blocking - don't fail if profiling fails)
            import logging
            logger = logging.getLogger(__name__)
            try:
                logger.info(f"Starting automatic profiling for voice: {name} (ID: {voice_id})")
                if keywords:
                    logger.info(f"Using keywords for profiling: {keywords}")
                else:
                    logger.info("No keywords provided for profiling")
                
                profile = voice_profiler.profile_voice_from_audio(
                    voice_name=name,
                    voice_description=description,
                    keywords=keywords,
                    ollama_url=ollama_url,
                    ollama_model=ollama_model,
                )
                if profile:
                    # Ensure keywords are included in profile
                    if keywords:
                        profile["keywords"] = keywords
                    # Store profile in voice metadata
                    voice_storage.update_voice_profile(voice_id, profile)
                    logger.info(f"Successfully created and saved profile for voice: {name}")
                else:
                    logger.warning(f"Profile creation returned empty profile for voice: {name}")
            except RuntimeError as e:
                # RuntimeError means Ollama is not available or model missing - log as warning
                logger.warning(f"Could not profile voice {name}: {e}")
            except Exception as e:
                # Log error but don't fail voice creation
                logger.error(f"Failed to automatically profile voice {name}: {e}", exc_info=True)

            # Return voice metadata with validation feedback
            voice_data = voice_storage.get_voice(voice_id)
            voice_data["validation_feedback"] = validation_feedback
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
        seen_voices = set()

        # Get list of custom voice IDs to exclude symlinks
        custom_voice_ids = {v["id"] for v in voice_storage.list_voices()}

        # Add default voices from actual files in the directory.
        # If a voice has a short-name mapping (e.g. en-Alice_woman -> Alice),
        # expose only the short name to avoid duplicate entries in the UI.
        if self.default_voices_dir.exists():
            for voice_file in self.default_voices_dir.glob("*.wav"):
                full_name = voice_file.stem
                if full_name.startswith("."):
                    continue

                # Check if this is a symlink to a custom voice
                is_custom_symlink = False
                if voice_file.is_symlink():
                    try:
                        target_path = voice_file.resolve()
                        # Check if target is in a custom voice directory
                        if self.custom_voices_dir in target_path.parents:
                            is_custom_symlink = True
                    except (OSError, RuntimeError):
                        # If symlink is broken, skip it
                        continue

                # Skip if it's a symlink to a custom voice or if the name matches a custom voice ID
                if is_custom_symlink or full_name in custom_voice_ids:
                    continue

                # Prefer the short name for mapped voices.
                short_name = None
                for candidate_short, mapped_name in VOICE_NAME_MAPPING.items():
                    if mapped_name == full_name:
                        short_name = candidate_short
                        break

                if short_name:
                    if short_name not in seen_voices:
                        voices.append(
                            {
                                "id": short_name,
                                "name": short_name,
                                "description": f"Default VibeVoice voice: {short_name} (maps to {full_name})",
                                "type": "default",
                                "created_at": None,
                                "audio_files": None,
                            }
                        )
                        seen_voices.add(short_name)
                else:
                    # No mapping: expose full voice id.
                    if full_name not in seen_voices:
                        voices.append(
                            {
                                "id": full_name,
                                "name": full_name,
                                "description": f"Default VibeVoice voice: {full_name}",
                                "type": "default",
                                "created_at": None,
                                "audio_files": None,
                            }
                        )
                        seen_voices.add(full_name)

        # IMPORTANT:
        # Do not add hardcoded "default" voices that aren't present on disk.
        # This prevents the API/UX from listing voices that cannot be used on this host.

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

        # Check default voices based on files present in the demo voices directory.
        # This must align with list_all_voices(), which enumerates the directory contents.
        resolved = VOICE_NAME_MAPPING.get(voice_id, voice_id)
        voice_path = self.default_voices_dir / f"{resolved}.wav"
        if voice_path.exists():
            return {
                "id": voice_id,
                "name": voice_id,
                "description": f"Default VibeVoice voice: {voice_id}",
                "type": "default",
                "created_at": None,
                "audio_files": None,
            }

        return None

    def enhance_voice_profile(
        self,
        voice_id: str,
        keywords: List[str],
        ollama_url: Optional[str] = None,
        ollama_model: Optional[str] = None,
    ) -> dict:
        """
        Enhance voice profile with keywords.

        Args:
            voice_id: Voice identifier
            keywords: Keywords for enhancement

        Returns:
            Updated voice data with enhanced profile

        Raises:
            ValueError: If voice is not found
        """
        voice_data = voice_storage.get_voice(voice_id)
        if not voice_data:
            raise ValueError(f"Voice '{voice_id}' not found")

        # Get existing profile
        existing_profile = voice_storage.get_voice_profile(voice_id)

        # Enhance profile with keywords
        try:
            enhanced_profile = voice_profiler.enhance_profile_with_keywords(
                voice_name=voice_data.get("name", voice_id),
                existing_profile=existing_profile,
                keywords=keywords,
                ollama_url=ollama_url,
                ollama_model=ollama_model,
            )
            if enhanced_profile:
                voice_storage.update_voice_profile(voice_id, enhanced_profile)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to enhance profile for voice {voice_id}: {e}")
            raise ValueError(f"Failed to enhance profile: {e}") from e

        # Return updated voice data
        return voice_storage.get_voice(voice_id)

    def update_voice(
        self,
        voice_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Update voice metadata.

        Args:
            voice_id: Voice identifier
            name: New voice name (optional)
            description: New voice description (optional)

        Returns:
            Updated voice data

        Raises:
            ValueError: If voice is not found or is a default voice
        """
        voice_data = voice_storage.get_voice(voice_id)
        if not voice_data:
            raise ValueError(f"Voice '{voice_id}' not found")

        # Check if it's a default voice
        if voice_data.get("type") == "default" or self.is_default_voice(voice_data.get("name", "")):
            raise ValueError("Cannot update default voices")

        # Validate new name if provided
        if name is not None:
            if not name or not name.strip():
                raise ValueError("Voice name cannot be empty")
            if self.is_default_voice(name):
                raise ValueError(f"Voice name '{name}' is reserved for default voices")
            if voice_storage.name_exists(name, exclude_voice_id=voice_id):
                raise ValueError(f"Voice with name '{name}' already exists")

        # Update via storage
        updated = voice_storage.update_voice(
            voice_id=voice_id,
            name=name,
            description=description,
        )

        if not updated:
            raise ValueError(f"Failed to update voice '{voice_id}'")

        # Return updated voice data
        return voice_storage.get_voice(voice_id)

    def get_voice_by_name(self, name: str) -> Optional[dict]:
        """
        Get voice metadata by name (searches custom voices by name).

        Args:
            name: Voice name to search for

        Returns:
            Voice metadata dict or None if not found
        """
        # Check custom voices by name
        custom_voices = voice_storage.list_voices()
        for voice_data in custom_voices:
            if voice_data.get("name", "").lower() == name.lower():
                return voice_data

        # Check default voices
        if self.is_default_voice(name) or name in DEFAULT_VOICES:
            return {
                "id": name,
                "name": name,
                "description": f"Default VibeVoice voice: {name}",
                "type": "default",
                "created_at": None,
                "audio_files": None,
            }

        return None

    def ensure_voice_accessible(self, voice_name: str) -> str:
        """
        Ensure a voice file is accessible in the default voices directory.
        For custom voices, creates a symlink in the default voices directory.

        Args:
            voice_name: Voice name

        Returns:
            Resolved voice name (for default voices) or voice name (for custom voices)

        Raises:
            ValueError: If voice is not found
        """
        # Check if it's a default voice that needs mapping
        if voice_name in VOICE_NAME_MAPPING:
            return VOICE_NAME_MAPPING[voice_name]

        # Check if it's a default voice
        if self.is_default_voice(voice_name):
            return voice_name

        # Check if it's a custom voice
        voice_data = self.get_voice_by_name(voice_name)
        if voice_data and voice_data.get("type") == "custom":
            voice_id = voice_data.get("id")
            if not voice_id:
                raise ValueError(f"Custom voice '{voice_name}' has no ID")

            # Ensure default voices directory exists
            self.default_voices_dir.mkdir(parents=True, exist_ok=True)

            # Get source file path
            voice_dir = self.custom_voices_dir / voice_id
            source_path = voice_dir / "combined.wav"

            if not source_path.exists():
                raise ValueError(f"Voice file not found for '{voice_name}' at {source_path}")

            # Create symlink in default voices directory
            target_path = self.default_voices_dir / f"{voice_name}.wav"

            # Remove existing symlink/file if it exists
            if target_path.exists() or target_path.is_symlink():
                target_path.unlink()

            # Create symlink
            try:
                target_path.symlink_to(source_path)
            except OSError:
                # If symlink fails (e.g., on Windows), copy the file
                shutil.copy2(source_path, target_path)

            return voice_name

        # Return as-is if not found (will cause error in inference)
        return voice_name

    def resolve_voice_name(self, voice_name: str) -> str:
        """
        Resolve a voice name to its actual file name.

        Maps short names (e.g., "Alice") to full names (e.g., "en-Alice_woman").
        For custom voices, ensures they are accessible in the default voices directory.

        Args:
            voice_name: Voice name (short or full)

        Returns:
            Resolved voice name (full name if mapping exists, otherwise original)
        """
        return self.ensure_voice_accessible(voice_name)

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

        # Resolve voice name (map short names to full names)
        resolved_name = self.resolve_voice_name(voice_id)

        # Check default voices
        if self.default_voices_dir.exists():
            # Try exact match first
            exact_path = self.default_voices_dir / f"{resolved_name}.wav"
            if exact_path.exists():
                return exact_path

            # Try different naming conventions as fallback
            for pattern in [f"{resolved_name}.wav", f"{voice_id}.wav", f"en-{voice_id}.wav", f"{voice_id}_*.wav"]:
                matches = list(self.default_voices_dir.glob(pattern))
                if matches:
                    return matches[0]

        return None


# Global voice manager instance
voice_manager = VoiceManager()