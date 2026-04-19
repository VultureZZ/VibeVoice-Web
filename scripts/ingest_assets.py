#!/usr/bin/env python3
"""
Walk a source tree, analyze audio files, and add them to the local podcast asset library.

For each ``track.wav`` (or other supported extension), optionally reads ``track.json`` in the
same directory with metadata. Otherwise prompts for tags (unless ``--non-interactive``).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional

# Repo root on sys.path for ``app`` and ``src`` (vibevoice).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SRC = _ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

logger = logging.getLogger("ingest_assets")

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".aif", ".aiff", ".m4a"}


def _duration_ms_soundfile(path: Path) -> int:
    import soundfile as sf

    info = sf.info(str(path))
    return int(round(float(info.duration) * 1000.0))


def _duration_ms_librosa(path: Path) -> int:
    import librosa

    y, sr = librosa.load(str(path), sr=None, mono=True)
    return int(round(1000.0 * float(len(y)) / float(sr)))


def _duration_ms_wave_stdlib(path: Path) -> int:
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate() or 1
        return int(round(1000.0 * float(frames) / float(rate)))


def audio_duration_ms(path: Path) -> int:
    if path.suffix.lower() == ".wav":
        try:
            return _duration_ms_wave_stdlib(path)
        except Exception:
            pass
    try:
        return _duration_ms_soundfile(path)
    except Exception:
        return _duration_ms_librosa(path)


def estimate_bpm(path: Path) -> Optional[int]:
    """Rough BPM for music beds; may return None for ambience/SFX."""
    try:
        import librosa

        y, sr = librosa.load(str(path), sr=22050, mono=True)
        if len(y) < sr // 2:
            return None
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        t = float(tempo)
        if t != t or t < 30 or t > 300:
            return None
        return int(round(t))
    except Exception as exc:
        logger.debug("BPM estimate failed for %s: %s", path, exc)
        return None


def load_sidecar(path: Path) -> Optional[Dict[str, Any]]:
    side = path.with_suffix(".json")
    if not side.is_file():
        return None
    try:
        return json.loads(side.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Invalid JSON sidecar %s: %s", side, exc)
        return None


def _prompt_line(label: str, default: str = "") -> str:
    try:
        raw = input(f"{label} [{default}]: ").strip()
    except EOFError:
        raw = ""
    return raw or default


def _prompt_int(label: str, default: int, min_v: int, max_v: int) -> int:
    raw = _prompt_line(label, str(default))
    try:
        v = int(raw)
        return max(min_v, min(max_v, v))
    except ValueError:
        return default


def _prompt_tags(label: str, default_csv: str) -> List[str]:
    raw = _prompt_line(label, default_csv)
    return [x.strip().lower().replace(" ", "_") for x in raw.split(",") if x.strip()]


def collect_metadata(
    path: Path,
    *,
    non_interactive: bool,
    estimate_bpm_flag: bool,
    default_category: str,
    sidecar: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    data = dict(sidecar or {})
    data["duration_ms"] = audio_duration_ms(path)

    if "category" not in data:
        if non_interactive:
            data["category"] = default_category
        else:
            data["category"] = _prompt_line("category", default_category)

    cat = str(data["category"])
    music_like = cat.startswith("music_")

    if "genre_tags" not in data:
        if non_interactive:
            data["genre_tags"] = ["news"]
        else:
            data["genre_tags"] = _prompt_tags(
                "genre_tags (comma, e.g. news,true_crime)", "news"
            )

    if "mood_tags" not in data:
        if non_interactive:
            data["mood_tags"] = ["neutral"]
        else:
            data["mood_tags"] = _prompt_tags("mood_tags (comma)", "neutral")

    if "intensity" not in data:
        if non_interactive:
            data["intensity"] = 3
        else:
            data["intensity"] = _prompt_int("intensity (1-5)", 3, 1, 5)

    if "source" not in data:
        data["source"] = "user_uploaded"

    if "licensing" not in data:
        data["licensing"] = "user; verify rights before distribution"

    if estimate_bpm_flag and music_like and "bpm" not in data:
        bpm = estimate_bpm(path)
        if bpm is not None:
            data["bpm"] = bpm

    return data


def iter_audio_files(source: Path) -> List[Path]:
    out: List[Path] = []
    if source.is_file():
        if source.suffix.lower() in AUDIO_EXTENSIONS:
            return [source]
        return []
    for p in sorted(source.rglob("*")):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS:
            out.append(p)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest audio files into the local asset library.")
    parser.add_argument("source", type=Path, help="File or directory to walk")
    parser.add_argument(
        "--library-root",
        type=Path,
        default=None,
        help="Override ASSET_LIBRARY_ROOT / default assets/library",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Use defaults when sidecar JSON is missing fields",
    )
    parser.add_argument(
        "--default-category",
        default="music_bed",
        help="Category used in non-interactive mode when unspecified",
    )
    parser.add_argument(
        "--estimate-bpm",
        action="store_true",
        help="Estimate BPM with librosa for music-like categories when bpm not in sidecar",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    from app.services.asset_library import AssetLibrary

    lib = AssetLibrary(args.library_root)
    lib.ensure_layout_dirs()

    files = iter_audio_files(args.source)
    if not files:
        logger.error("No supported audio files under %s", args.source)
        return 1

    added = 0
    for path in files:
        side = load_sidecar(path)
        meta = collect_metadata(
            path,
            non_interactive=args.non_interactive,
            estimate_bpm_flag=args.estimate_bpm,
            default_category=args.default_category,
            sidecar=side,
        )
        try:
            aid = lib.add_asset(path, meta)
            logger.info("Added %s -> %s", path.name, aid)
            added += 1
        except Exception as exc:
            logger.exception("Failed to add %s: %s", path, exc)

    logger.info("Done. Added %d asset(s).", added)
    return 0 if added else 1


if __name__ == "__main__":
    raise SystemExit(main())
