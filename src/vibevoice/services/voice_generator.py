"""
Voice generation service.

Wraps VibeVoice inference logic to generate speech from text.
"""
import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..config import config
from .voice_manager import voice_manager

logger = logging.getLogger(__name__)


class VoiceGenerator:
    """Service for generating speech from text."""

    def __init__(self):
        """Initialize voice generator."""
        self.model_path = config.MODEL_PATH
        self.output_dir = config.OUTPUT_DIR
        self.vibevoice_repo_dir = config.VIBEVOICE_REPO_DIR
        self.inference_script = self.vibevoice_repo_dir / "demo" / "inference_from_file.py"
        
        logger.info("VoiceGenerator initialized")
        logger.info(f"  Model path: {self.model_path}")
        logger.info(f"  Output directory: {self.output_dir}")
        logger.info(f"  VibeVoice repo: {self.vibevoice_repo_dir}")
        logger.info(f"  Inference script: {self.inference_script}")

    def validate_speakers(self, speakers: List[str]) -> None:
        """
        Validate that all speakers exist.

        Args:
            speakers: List of speaker names (canonical or mapped format)

        Raises:
            ValueError: If any speaker is invalid
        """
        logger.debug(f"Validating speakers: {speakers}")

        # Normalize speaker names to canonical form (case-insensitive)
        normalized_speakers = [voice_manager.normalize_voice_name(s) for s in speakers]
        logger.debug(f"Normalized speakers: {normalized_speakers}")

        all_voices = voice_manager.list_all_voices()
        available_names = {v["name"] for v in all_voices}
        logger.debug(f"Available voices: {sorted(available_names)}")

        # Validate normalized names (normalize_voice_name should return correctly-cased names)
        # Use case-insensitive matching as a safety measure
        available_names_lower = {name.lower(): name for name in available_names}
        invalid_speakers = []
        for normalized in normalized_speakers:
            if normalized.lower() not in available_names_lower:
                invalid_speakers.append(normalized)
        
        if invalid_speakers:
            logger.error(f"Invalid speakers detected: {invalid_speakers}")
            raise ValueError(f"Invalid speakers: {', '.join(invalid_speakers)}")

        logger.info(f"Speaker validation passed: {speakers} (normalized: {normalized_speakers})")

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
        logger.info("Starting speech generation process...")
        logger.info(f"  Transcript length: {len(transcript)} characters")
        logger.info(f"  Speakers: {speakers}")
        logger.info(f"  Output filename: {output_filename or 'auto-generated'}")

        # Validate speakers
        logger.info("Validating speakers...")
        self.validate_speakers(speakers)

        # Validate model and inference script exist
        logger.info("Checking model and inference script...")
        if not self.model_path.exists():
            logger.error(f"Model not found at {self.model_path}")
            raise RuntimeError(f"Model not found at {self.model_path}")
        logger.info(f"  Model path verified: {self.model_path}")
        
        # Check model files
        model_files = list(self.model_path.glob("*.safetensors")) + list(self.model_path.glob("*.bin"))
        logger.info(f"  Model files found: {len(model_files)}")

        if not self.inference_script.exists():
            logger.error(f"Inference script not found at {self.inference_script}")
            raise RuntimeError(f"Inference script not found at {self.inference_script}")
        logger.info(f"  Inference script verified: {self.inference_script}")

        # Create transcript file
        logger.info("Creating temporary transcript file...")
        transcript_file = self.create_transcript_file(transcript)
        logger.info(f"  Transcript file created: {transcript_file}")

        try:
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Generate output filename if not provided
            if output_filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"{timestamp}_generated.wav"

            output_path = self.output_dir / output_filename

            # Resolve speaker names (map short names like "Alice" to full names like "en-Alice_woman")
            logger.info("Resolving speaker names to voice file names...")
            resolved_speakers = []
            for speaker in speakers:
                resolved = voice_manager.resolve_voice_name(speaker)
                resolved_speakers.append(resolved)
                if resolved != speaker:
                    logger.info(f"  '{speaker}' -> '{resolved}'")
                else:
                    logger.info(f"  '{speaker}' (no mapping needed)")
            logger.info(f"Resolved speakers: {resolved_speakers}")

            # Build command
            cmd = [
                sys.executable,
                str(self.inference_script),
                "--model_path",
                str(self.model_path),
                "--txt_path",
                str(transcript_file),
                "--speaker_names",
            ] + resolved_speakers

            logger.info("")
            logger.info("Executing VibeVoice Inference")
            logger.info("-" * 80)
            logger.info(f"Command: {' '.join(cmd)}")
            logger.info(f"Working directory: {config.PROJECT_ROOT}")
            logger.info(f"Python executable: {sys.executable}")
            logger.info("")

            # Check for CUDA availability
            try:
                import torch
                if torch.cuda.is_available():
                    logger.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
                    logger.info(f"CUDA device count: {torch.cuda.device_count()}")
                else:
                    logger.warning("CUDA not available - will use CPU (slower)")
            except ImportError:
                logger.warning("PyTorch not available for CUDA check")

            logger.info("")
            logger.info("Running inference (this may take a while)...")
            start_time = datetime.now()

            # Run inference
            try:
                # IMPORTANT: Ensure the subprocess imports VibeVoice code from the checked-out
                # repo (config.VIBEVOICE_REPO_DIR). This avoids conflicts when another repo
                # (e.g. microsoft/VibeVoice for realtime) is installed in the same venv under
                # the same `vibevoice` package name.
                env = os.environ.copy()
                repo_pythonpath = str(self.vibevoice_repo_dir)
                env["PYTHONPATH"] = repo_pythonpath + os.pathsep + env.get("PYTHONPATH", "")

                result = subprocess.run(
                    cmd,
                    cwd=str(config.PROJECT_ROOT),
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logger.info(f"Inference completed in {duration:.2f} seconds")
                
                # Log output if available
                if result.stdout:
                    logger.debug("Inference stdout:")
                    for line in result.stdout.split("\n")[:20]:  # First 20 lines
                        if line.strip():
                            logger.debug(f"  {line}")
                
            except subprocess.CalledProcessError as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logger.error(f"Inference failed after {duration:.2f} seconds")
                logger.error(f"Exit code: {e.returncode}")
                if e.stdout:
                    logger.error("STDOUT:")
                    for line in e.stdout.split("\n")[-50:]:  # Last 50 lines
                        if line.strip():
                            logger.error(f"  {line}")
                if e.stderr:
                    logger.error("STDERR:")
                    for line in e.stderr.split("\n")[-50:]:  # Last 50 lines
                        if line.strip():
                            logger.error(f"  {line}")
                error_msg = f"Inference failed: {e.stderr or e.stdout or 'Unknown error'}"
                raise RuntimeError(error_msg) from e

            # Find the generated file
            logger.info("")
            logger.info("Locating generated audio file...")
            logger.info(f"  Output directory: {self.output_dir}")
            
            # VibeVoice typically generates files with "generated" in the name
            generated_files = list(self.output_dir.glob("*generated.wav"))
            logger.info(f"  Found {len(generated_files)} generated .wav file(s)")
            
            if generated_files:
                # Get the most recent file
                latest_file = max(generated_files, key=lambda p: p.stat().st_mtime)
                logger.info(f"  Most recent file: {latest_file}")
                logger.info(f"  File size: {latest_file.stat().st_size / 1024 / 1024:.2f} MB")
                logger.info(f"  Modified: {datetime.fromtimestamp(latest_file.stat().st_mtime)}")
                
                # Rename to our desired output filename if different
                if latest_file != output_path:
                    logger.info(f"  Renaming to: {output_path}")
                    latest_file.rename(output_path)
                else:
                    logger.info(f"  File already has correct name: {output_path}")
                
                logger.info(f"Final output file: {output_path}")
                return output_path
            else:
                # If no file found, check if output_path was created
                logger.warning(f"No generated files found with pattern '*generated.wav'")
                logger.info(f"Checking if output path exists: {output_path}")
                if output_path.exists():
                    logger.info(f"Output file found at expected path: {output_path}")
                    return output_path
                logger.error("Generated audio file not found")
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
