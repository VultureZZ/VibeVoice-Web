"""
Voice generation service.

Wraps VibeVoice inference logic to generate speech from text.
"""
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..config import config
from .voice_manager import voice_manager


class VoiceGenerator:
    """Service for generating speech from text."""

    def __init__(self):
        """Initialize voice generator."""
        self.model_path = config.MODEL_PATH
        self.output_dir = config.OUTPUT_DIR
        self.vibevoice_repo_dir = config.VIBEVOICE_REPO_DIR
        self.inference_script = self.vibevoice_repo_dir / "demo" / "inference_from_file.py"

    def validate_speakers(self, speakers: List[str]) -> None:
        """
        Validate that all speakers exist.

        Args:
            speakers: List of speaker names

        Raises:
            ValueError: If any speaker is invalid
        """
        all_voices = voice_manager.list_all_voices()
        available_names = {v["name"] for v in all_voices}

        invalid_speakers = [s for s in speakers if s not in available_names]
        if invalid_speakers:
            raise ValueError(f"Invalid speakers: {', '.join(invalid_speakers)}")

    def create_transcript_file(self, transcript: str) -> Path:
        """
        Create a temporary transcript file.

        Args:
            transcript: Transcript text with speaker labels

        Returns:
            Path to temporary transcript file
        """
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            prefix="transcript_",
        )
        temp_file.write(transcript)
        temp_file.close()
        return Path(temp_file.name)

    def generate_speech(
        self,
        transcript: str,
        speakers: List[str],
        output_filename: Optional[str] = None,
    ) -> Path:
        """
        Generate speech from transcript.

        Args:
            transcript: Transcript text with speaker labels (e.g., "Speaker 1: Hello")
            speakers: List of speaker names
            output_filename: Optional custom output filename

        Returns:
            Path to generated audio file

        Raises:
            ValueError: If speakers are invalid or generation fails
            RuntimeError: If inference script fails
        """
        # Validate speakers
        self.validate_speakers(speakers)

        # Validate model and inference script exist
        if not self.model_path.exists():
            raise RuntimeError(f"Model not found at {self.model_path}")

        if not self.inference_script.exists():
            raise RuntimeError(f"Inference script not found at {self.inference_script}")

        # Create transcript file
        transcript_file = self.create_transcript_file(transcript)

        try:
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Generate output filename if not provided
            if output_filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"{timestamp}_generated.wav"

            output_path = self.output_dir / output_filename

            # Build command
            cmd = [
                sys.executable,
                str(self.inference_script),
                "--model_path",
                str(self.model_path),
                "--txt_path",
                str(transcript_file),
                "--speaker_names",
            ] + speakers

            # Run inference
            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(config.PROJECT_ROOT),
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                error_msg = f"Inference failed: {e.stderr or e.stdout or 'Unknown error'}"
                raise RuntimeError(error_msg) from e

            # Find the generated file
            # VibeVoice typically generates files with "generated" in the name
            generated_files = list(self.output_dir.glob("*generated.wav"))
            if generated_files:
                # Get the most recent file
                latest_file = max(generated_files, key=lambda p: p.stat().st_mtime)
                # Rename to our desired output filename if different
                if latest_file != output_path:
                    latest_file.rename(output_path)
                return output_path
            else:
                # If no file found, check if output_path was created
                if output_path.exists():
                    return output_path
                raise RuntimeError("Generated audio file not found")

        finally:
            # Clean up transcript file
            if transcript_file.exists():
                transcript_file.unlink()

    def format_transcript(self, transcript: str, speakers: List[str]) -> str:
        """
        Format transcript to ensure proper speaker labels.

        Args:
            transcript: Raw transcript text
            speakers: List of speaker names

        Returns:
            Formatted transcript with speaker labels
        """
        # If transcript already has speaker labels, return as-is
        if "Speaker" in transcript or ":" in transcript:
            return transcript

        # Otherwise, format with speaker labels
        lines = transcript.strip().split("\n")
        formatted_lines = []
        speaker_index = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Assign speaker in round-robin fashion
            speaker_name = speakers[speaker_index % len(speakers)]
            formatted_lines.append(f"Speaker {speaker_index + 1}: {line}")
            speaker_index += 1

        return "\n".join(formatted_lines)


# Global voice generator instance
voice_generator = VoiceGenerator()
