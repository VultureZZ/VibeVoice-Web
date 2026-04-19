#!/usr/bin/env python3
"""
Canary mix QA: render a fixed script through the production mixer (fallback plan) and
compare QA metric keys / summary shape against tests/baselines/mix_qa_baseline.json.

Exit 0 when structure matches; exit 1 on mismatch. Intended for CI (no GPU required
when using synthetic voice).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SRC = _ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

CANARY_SCRIPT = """Speaker 1: Canary line one for mix regression.
Speaker 2: Canary line two.
Speaker 1: End."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Mix QA regression vs baseline JSON.")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=_ROOT / "tests" / "baselines" / "mix_qa_baseline.json",
        help="Baseline JSON path",
    )
    args = parser.parse_args()

    import numpy as np
    import soundfile as sf

    from app.services.asset_library import AssetLibrary
    from app.services.mix_qa import run_mix_qa
    from app.services.production_director import build_fallback_production_plan, _fallback_segments_from_script
    from app.services.production_mixer import ProductionMixer

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    expected_checks = set(baseline.get("checks", []))
    expected_summary = set(baseline.get("summary_keys", []))

    td = Path(__file__).resolve().parent.parent / "output" / "mix_regression_tmp.wav"
    td.parent.mkdir(parents=True, exist_ok=True)
    sr = 48000
    dur = 5.0
    y = (np.random.default_rng(0).standard_normal(int(sr * dur)) * 0.05).astype(np.float32)
    sf.write(str(td), y, sr)

    segs = _fallback_segments_from_script(CANARY_SCRIPT)
    plan = build_fallback_production_plan(
        script=CANARY_SCRIPT,
        script_segments=segs,
        genre="Storytelling",
        episode_id="mix-regression",
        timing_hints=None,
    )
    out_mp3 = td.parent / "mix_regression_out.mp3"
    mixer = ProductionMixer()
    mixer.render(plan, str(td), str(out_mp3), library=AssetLibrary(), genre_template=None)

    qa = run_mix_qa(
        out_mp3,
        target_lufs=-16.0,
        plan_duration_seconds=float(plan.duration_target_seconds),
        dialogue_regions_ms=[(0, 4000)],
        plan=plan,
    )
    names = {c["name"] for c in qa.get("checks", [])}
    if not expected_checks <= names:
        print("MISSING checks:", expected_checks - names, file=sys.stderr)
        return 1
    sm = qa.get("summary") or {}
    if not expected_summary <= set(sm.keys()):
        print("MISSING summary keys:", expected_summary - set(sm.keys()), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "summary": sm}, indent=2))
    try:
        td.unlink(missing_ok=True)
        out_mp3.unlink(missing_ok=True)
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
