"""
Parse transcript with speaker labels into segments for per-speaker TTS.
"""
import re
from dataclasses import dataclass
from typing import List, Tuple

# Inline silence hint after a speaker line (stripped before synthesis). Example: [PAUSE_MS:220]
INLINE_PAUSE_MS_PATTERN = re.compile(r"\s*\[PAUSE_MS:\s*(\d{1,4})\s*\]", re.IGNORECASE)
_MAX_PAUSE_MS = 5000


def strip_inline_pause_markers(text: str) -> Tuple[str, int]:
    """
    Remove ``[PAUSE_MS:N]`` tokens from spoken text and return total milliseconds (capped).

    Multiple markers on one line sum; used for ``TranscriptSegment.pause_after_ms``.
    """
    if not text or not text.strip():
        return text, 0

    total = 0

    def _accum(m: re.Match) -> str:
        nonlocal total
        try:
            total += int(m.group(1))
        except ValueError:
            return ""
        return " "

    cleaned = INLINE_PAUSE_MS_PATTERN.sub(_accum, text)
    cleaned = re.sub(r" +", " ", cleaned).strip()
    return cleaned, min(_MAX_PAUSE_MS, max(0, total))


@dataclass
class TranscriptSegment:
    """A single segment of transcript attributed to one speaker."""

    speaker_index: int
    """Index into the speakers list (0-based)."""
    text: str
    """Plain text for this segment (no speaker label)."""
    instruct: str = ""
    """Qwen3-TTS style/emotion instruction for this utterance only (merged with SpeakerRef.instruct)."""
    pause_after_ms: int = 0
    """Silence appended after this segment in the output WAV (before WhisperX alignment)."""


def parse_transcript_into_segments(transcript: str, num_speakers: int) -> List[TranscriptSegment]:
    """
    Parse transcript with "Speaker N: ..." labels into a list of segments.

    Supports formats:
      - "Speaker 1: Hello world"
      - "Speaker 2: More text"
      - "Speaker 1: Continued"
      - Optional inline ``[PAUSE_MS:N]`` tokens (stripped from speech; summed into ``pause_after_ms``)

    Speaker indices are normalized to 0-based (Speaker 1 -> 0, Speaker 2 -> 1)
    and wrapped with num_speakers so they always index into the given speakers list.

    Args:
        transcript: Full transcript text with speaker labels.
        num_speakers: Number of speakers (length of the speakers list).

    Returns:
        List of TranscriptSegment in order.
    """
    if num_speakers < 1:
        raise ValueError("num_speakers must be at least 1")

    # Pattern: "Speaker N:" or "Speaker N :" at start of line (case-insensitive)
    pattern = re.compile(
        r"^\s*Speaker\s+(\d+)\s*:\s*(.*)$",
        re.IGNORECASE | re.MULTILINE,
    )

    segments: List[TranscriptSegment] = []
    last_end = 0

    for match in pattern.finditer(transcript):
        # Any text before this match belongs to the previous segment (or first speaker if none)
        if match.start() > last_end:
            pending = transcript[last_end : match.start()].strip()
            if pending:
                # Attribute to speaker 0 by default (will be overridden if we had a previous segment)
                prev_speaker = segments[-1].speaker_index if segments else 0
                t2, p2 = strip_inline_pause_markers(pending)
                if t2:
                    segments.append(
                        TranscriptSegment(speaker_index=prev_speaker, text=t2, pause_after_ms=p2)
                    )

        speaker_num = int(match.group(1))
        # 1-based to 0-based, then wrap
        speaker_index = (speaker_num - 1) % num_speakers
        raw_text = match.group(2).strip()
        text, pause_ms = strip_inline_pause_markers(raw_text)
        if text:
            segments.append(
                TranscriptSegment(speaker_index=speaker_index, text=text, pause_after_ms=pause_ms)
            )

        last_end = match.end()

    # Trailing text after last "Speaker N:"
    if last_end < len(transcript):
        pending = transcript[last_end:].strip()
        if pending:
            prev_speaker = segments[-1].speaker_index if segments else 0
            t2, p2 = strip_inline_pause_markers(pending)
            if t2:
                segments.append(
                    TranscriptSegment(speaker_index=prev_speaker, text=t2, pause_after_ms=p2)
                )

    # If no speaker labels were found, treat whole transcript as one segment (speaker 0)
    if not segments and transcript.strip():
        t0, p0 = strip_inline_pause_markers(transcript.strip())
        if t0:
            segments.append(TranscriptSegment(speaker_index=0, text=t0, pause_after_ms=p0))

    return segments
