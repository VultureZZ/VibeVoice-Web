"""
Audio validation service for voice training.

Analyzes audio files and provides feedback on duration, quality, and recommendations.
"""
from pathlib import Path
from typing import Dict, List, Optional

from pydub import AudioSegment


# Audio duration recommendations (in seconds)
MIN_DURATION_SECONDS = 30.0  # Minimum recommended duration
RECOMMENDED_MIN_DURATION = 60.0  # Recommended minimum (1 minute)
RECOMMENDED_MAX_DURATION = 180.0  # Recommended maximum (3 minutes)
MAX_RECOMMENDED_DURATION = 300.0  # Maximum recommended (5 minutes)

# Individual file recommendations
RECOMMENDED_FILE_MIN_DURATION = 3.0  # Minimum per file (3 seconds)
RECOMMENDED_FILE_MAX_DURATION = 10.0  # Maximum per file (10 seconds)

# Standard audio settings for VibeVoice
STANDARD_SAMPLE_RATE = 24000  # Hz
STANDARD_CHANNELS = 1  # Mono


class AudioValidator:
    """Service for validating audio files for voice training."""

    def analyze_file(self, audio_path: Path) -> Dict:
        """
        Analyze a single audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Dict with analysis results including duration, sample_rate, channels, file_size, warnings
        """
        try:
            # Load audio file
            audio = AudioSegment.from_file(str(audio_path))

            duration_seconds = len(audio) / 1000.0  # pydub returns milliseconds
            sample_rate = audio.frame_rate
            channels = audio.channels
            file_size_bytes = audio_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)

            warnings = []

            # Check duration
            if duration_seconds < RECOMMENDED_FILE_MIN_DURATION:
                warnings.append(
                    f"File duration ({duration_seconds:.1f}s) is below recommended minimum ({RECOMMENDED_FILE_MIN_DURATION}s)"
                )
            elif duration_seconds > RECOMMENDED_FILE_MAX_DURATION:
                warnings.append(
                    f"File duration ({duration_seconds:.1f}s) exceeds recommended maximum ({RECOMMENDED_FILE_MAX_DURATION}s)"
                )

            # Check sample rate (informational, will be normalized)
            if sample_rate != STANDARD_SAMPLE_RATE:
                # Not a warning, just informational since we normalize
                pass

            # Check channels (informational, will be converted to mono)
            if channels > STANDARD_CHANNELS:
                # Not a warning, just informational since we convert
                pass

            return {
                "filename": audio_path.name,
                "duration_seconds": round(duration_seconds, 2),
                "sample_rate": sample_rate,
                "channels": channels,
                "file_size_bytes": file_size_bytes,
                "file_size_mb": round(file_size_mb, 2),
                "warnings": warnings,
            }

        except Exception as e:
            return {
                "filename": audio_path.name,
                "error": str(e),
                "warnings": [f"Failed to analyze file: {str(e)}"],
            }

    def validate_audio_files(
        self, audio_files: List[Path], combined_duration_seconds: Optional[float] = None
    ) -> Dict:
        """
        Validate multiple audio files and generate feedback.

        Args:
            audio_files: List of paths to audio files
            combined_duration_seconds: Optional combined duration (if already calculated)

        Returns:
            Dict with validation feedback including warnings, recommendations, and metrics
        """
        individual_analyses = []
        all_warnings = []
        total_duration = 0.0

        # Analyze each file
        for audio_file in audio_files:
            analysis = self.analyze_file(audio_file)
            individual_analyses.append(analysis)
            total_duration += analysis.get("duration_seconds", 0.0)
            all_warnings.extend(analysis.get("warnings", []))

        # Use provided combined duration if available, otherwise calculate from individual files
        if combined_duration_seconds is not None:
            total_duration = combined_duration_seconds

        # Generate warnings based on total duration
        warnings = all_warnings.copy()
        recommendations = []

        if total_duration < MIN_DURATION_SECONDS:
            warnings.append(
                f"Total audio duration ({total_duration:.1f}s) is below minimum recommended ({MIN_DURATION_SECONDS}s). "
                "Voice quality may be poor."
            )
            recommendations.append(
                f"Add more audio to reach at least {MIN_DURATION_SECONDS} seconds for better results."
            )
        elif total_duration < RECOMMENDED_MIN_DURATION:
            recommendations.append(
                f"Total audio duration ({total_duration:.1f}s) is below recommended minimum ({RECOMMENDED_MIN_DURATION}s). "
                "Consider adding more audio for better voice quality."
            )
        elif total_duration > MAX_RECOMMENDED_DURATION:
            warnings.append(
                f"Total audio duration ({total_duration:.1f}s) exceeds recommended maximum ({MAX_RECOMMENDED_DURATION}s). "
                "Additional audio beyond this point may not significantly improve quality."
            )
            recommendations.append(
                f"Consider using {RECOMMENDED_MAX_DURATION}-{MAX_RECOMMENDED_DURATION} seconds for optimal results."
            )
        elif RECOMMENDED_MIN_DURATION <= total_duration <= RECOMMENDED_MAX_DURATION:
            recommendations.append(
                f"Total audio duration ({total_duration:.1f}s) is within the optimal range "
                f"({RECOMMENDED_MIN_DURATION}-{RECOMMENDED_MAX_DURATION}s)."
            )

        # File count recommendations
        file_count = len(audio_files)
        if file_count == 1:
            recommendations.append(
                "Consider using multiple audio files (3-10 seconds each) for better voice diversity."
            )
        elif file_count > 20:
            recommendations.append(
                "Using many small files is fine, but ensure total duration is within recommended range."
            )

        # Generate quality metrics summary
        quality_metrics = {
            "total_duration_seconds": round(total_duration, 2),
            "file_count": file_count,
            "standard_sample_rate": STANDARD_SAMPLE_RATE,
            "standard_channels": STANDARD_CHANNELS,
        }

        return {
            "total_duration_seconds": round(total_duration, 2),
            "individual_files": individual_analyses,
            "warnings": warnings,
            "recommendations": recommendations,
            "quality_metrics": quality_metrics,
        }