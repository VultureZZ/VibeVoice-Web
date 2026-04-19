"""
Pre-render short backchannel TTS clips per voice profile and register them in AssetLibrary.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, List

import soundfile as sf

from app.services.asset_library import DEFAULT_GENRE_TAGS, AssetLibrary

logger = logging.getLogger(__name__)

PHRASES = ("mm-hmm", "right", "yeah", "exactly", "huh", "wow")


def _slug(s: str) -> str:
    x = re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")
    return (x[:40] or "voice") if x else "voice"


def _phrase_slug(phrase: str) -> str:
    x = re.sub(r"[^a-z0-9]+", "_", phrase.lower()).strip("_")
    return x[:24] or "phrase"


class BackchannelSynth:
    """Generate and cache backchannel WAVs using the same VoiceGenerator as the episode."""

    def __init__(self, voice_generator: Any, voice_names: List[str]) -> None:
        self._vg = voice_generator
        self._voice_names = list(voice_names)

    def ensure_cached(self, library: AssetLibrary) -> None:
        """Idempotent: skip asset_ids already in the index."""
        for name in self._voice_names:
            for phrase in PHRASES:
                aid = f"bc_{_slug(name)}_{_phrase_slug(phrase)}"
                try:
                    library.get(aid)
                    continue
                except KeyError:
                    pass
                self._generate_one(library, name, phrase, aid)

    def _generate_one(self, library: AssetLibrary, voice_name: str, phrase: str, asset_id: str) -> None:
        transcript = f"Speaker 1: {phrase}\n"
        out = self._vg.generate_speech(transcript, [voice_name], output_filename=f"{asset_id}.wav")
        path = Path(out)
        if not path.is_file():
            logger.warning("Backchannel generation produced no file for %s", asset_id)
            return
        data, sr = sf.read(str(path), always_2d=True, dtype="float32")
        duration_ms = int(1000.0 * data.shape[0] / float(sr))
        tags = list(DEFAULT_GENRE_TAGS)
        meta = {
            "asset_id": asset_id,
            "category": "voice_backchannel",
            "genre_tags": tags,
            "mood_tags": ["dialogue", "reaction"],
            "intensity": 2,
            "source": "builtin",
            "licensing": "synthetic_tts",
            "duration_ms": duration_ms,
        }
        try:
            library.add_asset(path, meta)
            logger.info("Registered backchannel asset %s", asset_id)
        except ValueError as exc:
            logger.debug("Backchannel asset skip: %s", exc)


def ensure_backchannel_assets(voice_names: List[str], library: AssetLibrary) -> None:
    """Convenience: lazy-import VoiceGenerator and populate library."""
    from vibevoice.services.voice_generator import voice_generator

    BackchannelSynth(voice_generator, voice_names).ensure_cached(library)
