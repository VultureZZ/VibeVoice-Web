#!/usr/bin/env python3
"""
Generate additional library assets with ACE-Step for underpopulated (category, genre) pairs.

Intended to run as a long idle-time job: low priority, sleeps between tasks, stops after
``--max-generations`` unless set to 0 (unlimited; use with care).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SRC = _ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from app.services.asset_library import AssetCategory, AssetLibrary, DEFAULT_GENRE_TAGS
from app.services.library_seeds import pick_seed_round_robin

logger = logging.getLogger("hydrate_library")

# All categories that participate in the (category × genre_tag) coverage matrix.
_MATRIX_CATEGORIES: Tuple[AssetCategory, ...] = (
    "music_bed",
    "music_transition",
    "music_intro",
    "music_outro",
    "sfx_impact",
    "sfx_riser",
    "sfx_whoosh",
    "sfx_ambience",
    "sfx_laugh",
    "foley",
)


def _apply_nice(value: int) -> None:
    if value == 0:
        return
    try:
        os.nice(value)
    except OSError as exc:
        logger.warning("Could not adjust nice(%s): %s", value, exc)


def _to_wav(src: Path, dest: Path) -> None:
    """Write a WAV at ``dest`` from ``src`` (copy or decode)."""
    import soundfile as sf

    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".wav":
        shutil.copy2(src, dest)
        return
    try:
        import librosa

        y, sr = librosa.load(str(src), sr=None, mono=True)
        sf.write(str(dest), y, int(sr))
    except Exception as exc:
        logger.warning("librosa/soundfile conversion failed (%s); trying pydub", exc)
        from pydub import AudioSegment

        AudioSegment.from_file(str(src)).export(str(dest), format="wav")


def _duration_ms_for_file(path: Path) -> int:
    import soundfile as sf

    info = sf.info(str(path))
    return int(round(float(info.duration) * 1000.0))


def _build_acestep_payload(seed: Dict[str, Any]) -> Dict[str, Any]:
    caption = str(seed.get("caption") or "").strip()
    duration = float(seed.get("duration_seconds") or 30.0)
    instrumental = bool(seed.get("instrumental", True))
    payload: Dict[str, Any] = {
        "prompt": caption,
        "instrumental": instrumental,
        "thinking": True,
        "batch_size": 1,
        "inference_steps": 8,
        "seed": -1,
        "audio_format": "wav",
    }
    if duration > 0:
        payload["duration"] = duration
    bpm = seed.get("bpm")
    if isinstance(bpm, int) and 30 <= bpm <= 300:
        payload["bpm"] = bpm
    ks = (seed.get("keyscale") or "").strip()
    if ks:
        payload["keyscale"] = ks
    if instrumental:
        payload.pop("lyrics", None)
        payload.pop("vocal_language", None)
    return payload


async def _wait_for_music_task(music_generator: Any, task_id: str, poll_s: float) -> Dict[str, Any]:
    while True:
        st = await music_generator.get_status(task_id)
        status = st.get("status")
        if status == "succeeded":
            return st
        if status == "failed":
            raise RuntimeError(st.get("error") or "ACE-Step task failed")
        await asyncio.sleep(poll_s)


async def _generate_one(
    library: AssetLibrary,
    music_generator: Any,
    seed: Dict[str, Any],
    poll_s: float,
) -> None:
    category = str(seed["category"])
    genre_tag = str(seed.get("primary_genre_tag") or "news")
    payload = _build_acestep_payload(seed)
    task_id = await music_generator.generate_music(payload)
    result = await _wait_for_music_task(music_generator, task_id, poll_s)
    meta_list = result.get("metadata") or []
    if not meta_list:
        raise RuntimeError("ACE-Step returned no audio metadata")
    src_audio = Path(meta_list[0].get("file_path") or "")
    if not src_audio.is_file():
        raise RuntimeError(f"Missing output file: {src_audio}")

    with tempfile.TemporaryDirectory() as td:
        tmp_wav = Path(td) / "ingest.wav"
        _to_wav(src_audio, tmp_wav)
        if not tmp_wav.is_file():
            raise RuntimeError(f"Could not materialize WAV for {src_audio}")
        path_for_lib = tmp_wav
        duration_ms = _duration_ms_for_file(path_for_lib)

        mood = "neutral"
        cat = category
        if cat.startswith("sfx_") or cat == "foley":
            mood = "tense" if genre_tag == "true_crime" else "playful" if genre_tag == "comedy" else "neutral"
        elif cat == "music_transition":
            mood = "uplifting"
        elif cat in ("music_intro", "music_outro"):
            mood = "warm"

        library.add_asset(
            path_for_lib,
            {
                "category": category,
                "genre_tags": [genre_tag],
                "mood_tags": [mood],
                "intensity": 3 if cat.startswith("music") else 2,
                "source": "ace_step_generated",
                "licensing": "ACE-Step generated; verify local policy",
                "duration_ms": duration_ms,
                "bpm": seed.get("bpm") if isinstance(seed.get("bpm"), int) else None,
                "key": (seed.get("keyscale") or None),
            },
        )


def _pairs_needing_assets(library: AssetLibrary, target: int) -> List[Tuple[str, str, int]]:
    """Return list of (category, genre_tag, shortfall) sorted by largest gap first."""
    gaps: List[Tuple[str, str, int]] = []
    for cat in _MATRIX_CATEGORIES:
        for g in DEFAULT_GENRE_TAGS:
            have = library.count_by_category_and_genre_tag(cat, g)
            need = max(0, target - have)
            if need > 0:
                gaps.append((cat, g, need))
    gaps.sort(key=lambda x: -x[2])
    return gaps


async def _run(args: argparse.Namespace) -> int:
    _apply_nice(args.nice)

    from vibevoice.services.music_generator import music_generator

    library = AssetLibrary(args.library_root)
    library.ensure_layout_dirs()

    generations = 0
    seed_counter = 0
    while True:
        if args.max_generations > 0 and generations >= args.max_generations:
            logger.info("Reached --max-generations=%s; stopping.", args.max_generations)
            break

        gaps = _pairs_needing_assets(library, args.target)
        if not gaps:
            logger.info("All (category, genre) pairs have at least %s assets.", args.target)
            break

        cat, genre, shortfall = gaps[0]
        logger.info(
            "Next gap: %s / %s (need %s more; %s pairs still short)",
            cat,
            genre,
            shortfall,
            len(gaps),
        )
        seed = pick_seed_round_robin(cat, genre, seed_counter)
        seed_counter += 1

        if args.dry_run:
            logger.info("DRY RUN would generate: %s", seed.get("caption", "")[:120])
            generations += 1
            await asyncio.sleep(0)
            continue

        try:
            await _generate_one(
                library,
                music_generator,
                seed,
                poll_s=args.poll_seconds,
            )
            generations += 1
            logger.info("Hydrated one asset (%s total this run).", generations)
        except Exception as exc:
            logger.exception("Generation failed: %s", exc)
            await asyncio.sleep(max(5.0, args.sleep_seconds))

        if args.sleep_seconds > 0:
            logger.debug("Idle sleep %s s", args.sleep_seconds)
            await asyncio.sleep(args.sleep_seconds)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Hydrate asset library via ACE-Step.")
    parser.add_argument(
        "--library-root",
        type=Path,
        default=None,
        help="Library root (default: assets/library or ASSET_LIBRARY_ROOT)",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=10,
        help="Minimum assets per (category, genre_tag) pair",
    )
    parser.add_argument(
        "--max-generations",
        type=int,
        default=5,
        help="Max successful additions this invocation (0 = no limit)",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=60.0,
        help="Pause between generations (idle-friendly)",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=3.0,
        help="ACE-Step status poll interval",
    )
    parser.add_argument(
        "--nice",
        type=int,
        default=5,
        help="Add this value to process nice (Unix); 0 disables",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
