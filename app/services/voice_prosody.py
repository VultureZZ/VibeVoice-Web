"""
Helpers for ProductionPlan voice_direction → TTS segment instructions and timing hints.
"""

from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.asset_library import default_library_root

_SPEAKER_LINE = re.compile(r"^(Speaker\s+\d+):\s*(.+)$", re.IGNORECASE)


def dialogue_line_count(script: str) -> int:
    n = 0
    for raw in script.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if _SPEAKER_LINE.match(line):
            n += 1
    return n


def synthetic_timing_hints_from_segments(script_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Coarse per-line timing for pre-Whisper Director pass (ms)."""
    hints: List[Dict[str, Any]] = []
    t = 0
    idx = 0
    for seg in script_segments:
        if str(seg.get("segment_type") or "").lower() != "dialogue":
            continue
        dur_ms = int(float(seg.get("duration_hint") or 30.0) * 1000.0)
        text = str(seg.get("text") or "")
        sp = str(seg.get("speaker") or "Speaker 1")
        hints.append(
            {
                "line_index": idx,
                "start_ms": t,
                "end_ms": t + dur_ms,
                "speaker": sp,
                "text": text,
            }
        )
        t += dur_ms + 200
        idx += 1
    return hints


def resolve_breath_audio_path(explicit: Optional[Path] = None) -> Optional[Path]:
    """First match: env path, then library foley files containing 'breath'."""
    if explicit and explicit.is_file():
        return explicit
    root = default_library_root()
    for sub in ("sfx/foley", "sfx", "foley"):
        d = root / sub
        if not d.is_dir():
            continue
        for p in sorted(d.glob("**/*breath*")):
            if p.is_file() and p.suffix.lower() in (".wav", ".mp3", ".flac", ".ogg"):
                return p
        for p in sorted(d.glob("**/*.wav")):
            if p.is_file() and "breath" in p.name.lower():
                return p
    return None


def breath_after_indices(num_segments: int, rng: Optional[random.Random] = None) -> Tuple[Set[int], int]:
    """Indices of segments after which to insert a breath clip (before next line)."""
    r = rng or random.Random()
    if num_segments < 2:
        return set(), 2
    stride = r.randint(2, 4)
    out = {i for i in range(num_segments - 1) if (i + 1) % stride == 0}
    return out, stride


def fallback_voice_direction_for_script(script: str, genre: str) -> List[Dict[str, Any]]:
    """Deterministic per-line prosody when Ollama Director is unavailable."""
    g = (genre or "General").strip().lower()
    lines: List[Tuple[str, str]] = []
    for raw in script.split("\n"):
        line = raw.strip()
        if not line:
            continue
        m = _SPEAKER_LINE.match(line)
        if not m:
            continue
        lines.append((m.group(1).strip(), m.group(2).strip()))
    out: List[Dict[str, Any]] = []
    for i, (spk, _text) in enumerate(lines):
        if "news" in g:
            emo, pause = "neutral", 80
        elif "crime" in g or "true" in g:
            emo, pause = "tense", 220 if i % 4 == 3 else 120
        elif "comedy" in g:
            emo, pause = "amused", 0
        elif "story" in g:
            emo, pause = "warm", 160
        elif "tech" in g:
            emo, pause = "curious", 100
        else:
            emo, pause = "neutral", 120
        out.append(
            {
                "line_index": i,
                "speaker": spk,
                "style": "natural",
                "emotion": emo,
                "emphasis_words": [],
                "pause_after_ms": pause,
                "reverb_send": 0.08,
                "pan": 0.0,
            }
        )
    return out


def emotion_line_energy_db(emotion: str) -> float:
    """Target RMS offset (dB) for LINE_ENERGY_MATCHING."""
    e = (emotion or "neutral").strip().lower()
    return {
        "neutral": 0.0,
        "excited": 2.2,
        "somber": -2.5,
        "curious": 0.6,
        "confident": 1.2,
        "amused": 1.5,
        "tense": -1.2,
        "warm": 0.8,
    }.get(e, 0.0)
