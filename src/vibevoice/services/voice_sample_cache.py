"""
Cached short TTS previews for the Voices UI.

Saves generated WAVs under ``custom_voices/voice_samples/`` and reuses them until
the transcript, language, style instruction (from profile), or voice reference
material changes.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..config import config
from ..models.voice_storage import voice_storage
from .voice_generator import voice_generator
from .voice_manager import voice_manager

logger = logging.getLogger(__name__)

# Must stay in sync with frontend `VOICE_SAMPLE_TRANSCRIPT` in voiceSample.ts
VOICE_SAMPLE_TRANSCRIPT = (
    "Speaker 1: Short voice sample. Natural pacing and clear delivery for your projects."
)

SAMPLE_VERSION = "1"
MAX_STYLE_INSTRUCTION_CHARS = 1800


def _sanitize_voice_id_for_path(voice_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", voice_id.strip())
    return safe[:200] if len(safe) > 200 else safe or "voice"


def samples_dir() -> Path:
    d = config.CUSTOM_VOICES_DIR / "voice_samples"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sample_paths(voice_id: str) -> Tuple[Path, Path]:
    stem = _sanitize_voice_id_for_path(voice_id)
    base = samples_dir() / stem
    return base.with_suffix(".wav"), base.with_suffix(".json")


def invalidate_voice_sample_cache(voice_id: str) -> None:
    """Remove cached preview files for a voice (e.g. after profile or metadata edits)."""
    wav, meta = sample_paths(voice_id)
    for p in (wav, meta):
        try:
            if p.exists():
                p.unlink()
        except OSError as e:
            logger.debug("Could not remove sample cache %s: %s", p, e)


def build_style_instruction_from_profile(profile: Optional[Dict[str, Any]]) -> Optional[str]:
    """Match frontend ``buildProfileStyleInstruction`` (voiceSample.ts)."""
    if not profile or not isinstance(profile, dict):
        return None

    parts: list[str] = []

    profile_text = profile.get("profile_text")
    if isinstance(profile_text, str) and profile_text.strip():
        parts.append(profile_text.strip())
    else:
        if profile.get("cadence"):
            parts.append(f"Cadence: {str(profile['cadence']).strip()}")
        if profile.get("tone"):
            parts.append(f"Tone: {str(profile['tone']).strip()}")
        if profile.get("vocabulary_style"):
            parts.append(f"Vocabulary: {str(profile['vocabulary_style']).strip()}")
        if profile.get("sentence_structure"):
            parts.append(f"Sentence style: {str(profile['sentence_structure']).strip()}")
        phrases = profile.get("unique_phrases") or []
        if isinstance(phrases, list) and phrases:
            cleaned = [str(p).strip() for p in phrases if str(p).strip()][:8]
            if cleaned:
                parts.append("Typical phrases: " + "; ".join(cleaned))
        keywords = profile.get("keywords") or []
        if isinstance(keywords, list) and keywords:
            kw = [str(k).strip() for k in keywords if str(k).strip()][:12]
            if kw:
                parts.append("Context: " + ", ".join(kw))

    if not parts:
        return None

    combined = "\n".join(parts)
    if len(combined) > MAX_STYLE_INSTRUCTION_CHARS:
        combined = combined[:MAX_STYLE_INSTRUCTION_CHARS].rstrip() + "…"

    return combined


def _voice_reference_fingerprint(voice_id: str, voice_data: Dict[str, Any]) -> str:
    """
    Changes when clone reference audio or voice-design prompt changes (invalidates cache).
    """
    vtype = voice_data.get("type", "custom")

    if vtype == "voice_design":
        prof = voice_data.get("profile") if isinstance(voice_data.get("profile"), dict) else {}
        prompt = (prof.get("voice_design_prompt") or voice_data.get("voice_design_prompt") or "").strip()
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:24]

    path = voice_manager.get_voice_path(voice_id)
    if path and path.exists():
        try:
            return str(path.stat().st_mtime_ns)
        except OSError:
            return "0"
    return "0"


def _content_hash(
    language: str,
    style_instruction: Optional[str],
    ref_fp: str,
) -> str:
    payload = "|".join(
        [
            SAMPLE_VERSION,
            VOICE_SAMPLE_TRANSCRIPT,
            language.strip().lower(),
            style_instruction or "",
            ref_fp,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_or_create_voice_sample(
    voice_id: str,
    *,
    language: str,
) -> Path:
    """
    Return path to a WAV preview for ``voice_id``, generating and caching on miss.

    Args:
        voice_id: Voice identifier (custom UUID or default short name like ``Alice``).
        language: BCP-ish language code used for TTS (e.g. ``en``, ``zh``).

    Returns:
        Path to cached ``.wav`` file.

    Raises:
        ValueError: Unknown voice or generation failure.
    """
    voice_data = voice_manager.get_voice(voice_id)
    if not voice_data:
        raise ValueError(f"Voice not found: {voice_id}")

    voice_name = voice_data.get("name") or voice_id
    profile = voice_storage.get_voice_profile(voice_id)
    style = build_style_instruction_from_profile(profile)
    ref_fp = _voice_reference_fingerprint(voice_id, voice_data)
    lang = (language or "en").strip().lower() or "en"
    chash = _content_hash(lang, style, ref_fp)

    wav_path, meta_path = sample_paths(voice_id)

    if wav_path.exists() and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("content_hash") == chash:
                return wav_path
        except (json.JSONDecodeError, OSError, TypeError):
            pass

    speaker_instructions = [style.strip()] if style and style.strip() else None

    output_filename = f"_tmp_sample_{uuid.uuid4().hex}.wav"
    out = voice_generator.generate_speech(
        transcript=VOICE_SAMPLE_TRANSCRIPT,
        speakers=[voice_name],
        language=lang,
        speaker_instructions=speaker_instructions,
        output_filename=output_filename,
    )

    try:
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        # Move off outputs/ (may be a different filesystem than custom_voices).
        if wav_path.exists():
            wav_path.unlink()
        shutil.move(str(out), str(wav_path))

        meta_payload = json.dumps(
            {
                "content_hash": chash,
                "language": lang,
                "voice_id": voice_id,
                "sample_version": SAMPLE_VERSION,
            },
            indent=2,
        )
        meta_part = meta_path.with_suffix(".json.part")
        meta_part.write_text(meta_payload, encoding="utf-8")
        meta_part.replace(meta_path)
    except OSError as e:
        logger.error("Failed to save voice sample cache: %s", e)
        raise ValueError(f"Failed to save voice sample: {e}") from e

    return wav_path
