"""
TTS backend interface and shared types.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

from .segments import TranscriptSegment


@dataclass
class SpeakerRef:
    """
    Reference to a speaker for TTS generation.

    - For default/built-in voices: use_custom_voice=True, speaker_id is the
      engine's built-in speaker name (e.g. Qwen3 "Vivian", "Ryan").
    - For custom/cloned voices: use_custom_voice=False, ref_audio_path points
      to the reference WAV; optional voice_clone_prompt is the engine-specific
      cached prompt (e.g. Qwen3 create_voice_clone_prompt result).
    """

    use_custom_voice: bool
    """True = use engine built-in speaker (speaker_id). False = use clone (ref_audio_path / voice_clone_prompt)."""
    speaker_id: str = ""
    """Built-in speaker name (e.g. Vivian, Ryan). Used when use_custom_voice=True."""
    ref_audio_path: Path | None = None
    """Path to reference WAV for cloning. Used when use_custom_voice=False."""
    ref_text: str | None = None
    """Transcript of reference audio (optional; some engines allow x_vector_only_mode without it)."""
    voice_clone_prompt: Any = None
    """Cached engine-specific clone prompt (e.g. Qwen3 prompt items). Optional."""


class TTSBackend(ABC):
    """Abstract base for TTS backends (Qwen3-TTS, XTTS, Bark)."""

    @abstractmethod
    def generate(
        self,
        segments: List[TranscriptSegment],
        speaker_refs: List[SpeakerRef],
        language: str,
        output_path: Path,
    ) -> Path:
        """
        Generate speech from transcript segments and write to output_path.

        Args:
            segments: List of (speaker_index, text) segments in order.
            speaker_refs: SpeakerRef for each distinct speaker (indexed by speaker_index in segments).
            language: Language code (e.g. "en", "Chinese").
            output_path: Path to write the final WAV.

        Returns:
            output_path after writing.
        """
        pass
