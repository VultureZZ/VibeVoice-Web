#!/usr/bin/env python3
"""
Render the same short script through ProductionMixer once per GenreTemplate for A/B comparison.

Outputs one MP3 per template under the configured output directory (or --out-dir).
Requires a voice WAV (use --voice); optional --duration-sec to trim/pad expectations.

Example:
  .venv/bin/python scripts/audition_genre.py --voice /path/to/voice_30s.wav
"""

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SRC = _ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

logger = logging.getLogger("audition_genre")

# ~30s of spoken content at typical pace (segmentation will add intro/outro/sting).
AUDITION_SCRIPT = """Speaker 1: Welcome back. In the next thirty seconds we will stress the production pipeline.
Speaker 2: Same words, same timing — only the genre template changes under the hood.
Speaker 1: You should hear differences in loudness targets, reverb, and mastering.
Speaker 2: If everything sounds identical, the templates are not wired through the mixer."""


def _ensure_wav_voice(path: Path, duration_sec: float) -> Path:
    """Return a stereo float WAV at 48kHz of the given duration (pink-ish noise if missing)."""
    import numpy as np
    import soundfile as sf

    if path.is_file():
        data, sr = sf.read(str(path), always_2d=True, dtype="float32")
        x = data.T
        target_len = int(duration_sec * sr)
        if x.shape[1] > target_len:
            x = x[:, :target_len]
        elif x.shape[1] < target_len:
            pad = target_len - x.shape[1]
            x = np.pad(x, ((0, 0), (0, pad)), mode="constant")
        out = Path(tempfile.gettempdir()) / f"audition_voice_{path.stem}.wav"
        sf.write(str(out), x.T, sr, subtype="PCM_24")
        return out

    sr = 48000
    n = int(duration_sec * sr)
    rng = np.random.default_rng(42)
    mono = rng.standard_normal(n).astype(np.float32) * 0.08
    b = np.cumsum(mono)
    b -= np.linspace(b[0], b[-1], n)
    pink = b / (np.max(np.abs(b)) + 1e-9) * 0.2
    stereo = np.stack([pink, pink])
    out = Path(tempfile.gettempdir()) / "audition_voice_synthetic.wav"
    sf.write(str(out), stereo.T, sr, subtype="PCM_24")
    logger.warning("No --voice file; wrote synthetic noise to %s", out)
    return out


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Audition all GenreTemplate profiles on one script.")
    parser.add_argument(
        "--voice",
        type=Path,
        default=None,
        help="Input voice WAV (if omitted, synthetic noise is generated)",
    )
    parser.add_argument("--duration-sec", type=float, default=30.0, help="Target voice duration (default 30)")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: vibevoice OUTPUT_DIR / audition_genre)",
    )
    args = parser.parse_args()

    from app.services.asset_library import AssetLibrary
    from app.services.genre_templates import TEMPLATES
    from app.services.production_director import build_fallback_production_plan, _fallback_segments_from_script
    from app.services.production_mixer import ProductionMixer

    try:
        from vibevoice.config import config  # type: ignore

        out_root = args.out_dir or (config.OUTPUT_DIR / "audition_genre")
    except Exception:
        out_root = args.out_dir or (_ROOT / "output" / "audition_genre")

    out_root.mkdir(parents=True, exist_ok=True)
    voice_wav = _ensure_wav_voice(args.voice or Path("/nonexistent"), args.duration_sec)

    segments = _fallback_segments_from_script(AUDITION_SCRIPT)
    plan = build_fallback_production_plan(
        script=AUDITION_SCRIPT,
        script_segments=segments,
        genre="Storytelling",
        episode_id="audition-episode",
        timing_hints=None,
    )
    lib = AssetLibrary()
    mixer = ProductionMixer()

    for tid, template in TEMPLATES.items():
        dest = out_root / f"audition_{tid}.mp3"
        logger.info("Rendering %s -> %s", template.display_name, dest)
        mixer.render(
            plan,
            str(voice_wav),
            str(dest),
            library=lib,
            genre_template=template,
        )

    logger.info("Done. Compare files in %s", out_root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
