"""
Post-render QA metrics for production mixes (LUFS, PLR, intelligibility proxy, gaps, clips).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

CheckResult = Dict[str, Any]


def _check_result(
    name: str,
    *,
    passed: bool,
    value: Any,
    threshold: str,
    severity: str = "fail",
) -> CheckResult:
    return {
        "name": name,
        "passed": passed,
        "value": value,
        "threshold": threshold,
        "severity": severity if not passed else "info",
    }


def _load_audio(path: Path) -> Tuple[np.ndarray, int]:
    """Return mono float32 in [-1, 1] and sample rate."""
    suf = path.suffix.lower()
    if suf in (".mp3", ".m4a", ".ogg"):
        try:
            import librosa

            y, sr = librosa.load(str(path), sr=None, mono=True)
            return np.asarray(y, dtype=np.float32), int(sr)
        except Exception:
            from pydub import AudioSegment

            seg = AudioSegment.from_file(str(path))
            seg = seg.set_channels(1)
            sr = int(seg.frame_rate)
            raw = np.array(seg.get_array_of_samples(), dtype=np.float32)
            maxv = float(2 ** (8 * seg.sample_width - 1))
            raw /= maxv
            return raw, sr
    import soundfile as sf

    data, sr = sf.read(str(path), always_2d=True, dtype="float32")
    mono = (data[:, 0] + data[:, 1]) / 2.0 if data.shape[1] > 1 else data[:, 0]
    return np.asarray(mono, dtype=np.float32), int(sr)


def _integrated_lufs(y: np.ndarray, sr: int) -> float:
    import pyloudnorm as pyln

    if y.size == 0:
        return -70.0
    x = np.asarray(y, dtype=np.float64)
    if x.ndim == 1:
        interleaved = np.column_stack([x, x])
    else:
        interleaved = x
    meter = pyln.Meter(sr)
    try:
        return float(meter.integrated_loudness(interleaved))
    except Exception as exc:
        logger.warning("LUFS measurement failed: %s", exc)
        return -70.0


def _sample_peak_dbfs(y: np.ndarray) -> float:
    peak = float(np.max(np.abs(y))) if y.size else 0.0
    return float(20.0 * np.log10(max(peak, 1e-12)))


def _clip_count(y: np.ndarray, thr: float = 0.999) -> int:
    return int(np.sum(np.abs(y) >= thr))


def _longest_silence_gap_ms(y: np.ndarray, sr: int, silence_db: float = -50.0, hop_ms: int = 20) -> float:
    """Longest contiguous low-energy region in ms."""
    if y.size == 0:
        return 0.0
    hop = max(1, int(sr * hop_ms / 1000.0))
    n = int(np.ceil(len(y) / hop))
    rms = np.zeros(n, dtype=np.float64)
    for i in range(n):
        sl = y[i * hop : min(len(y), (i + 1) * hop)]
        if sl.size:
            rms[i] = float(np.sqrt(np.mean(sl.astype(np.float64) ** 2)))
    ref = max(float(np.max(rms)), 1e-12)
    db = 20.0 * np.log10(np.maximum(rms / ref, 1e-12))
    silent = db < silence_db
    max_run = 0
    run = 0
    for v in silent:
        if v:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    return float(max_run * hop_ms)


def _plr_estimate(peak_dbfs: float, integrated_lufs: float) -> float:
    """Peak-to-loudness ratio (LU): sample peak dBFS minus integrated loudness (LUFS)."""
    return float(peak_dbfs - integrated_lufs)


def _band_ratio_db_dialogue(
    y: np.ndarray,
    sr: int,
    dialogue_regions_ms: Optional[List[Tuple[int, int]]],
) -> Tuple[float, bool]:
    """
    Compare STFT energy in 300–3400 Hz vs 50–300 Hz during dialogue.
    Returns (ratio_db, evaluated_any_frames).
    """
    try:
        import librosa
    except ImportError:
        return 0.0, False

    if y.size < 512:
        return 0.0, False

    n_fft = 2048
    hop = 512
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    low = (freqs >= 50.0) & (freqs <= 300.0)
    mid = (freqs >= 300.0) & (freqs <= 3400.0)
    times = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=hop, n_fft=n_fft)
    times_ms = (times * 1000.0).astype(np.float64)

    def _in_dialogue(t_ms: float) -> bool:
        if not dialogue_regions_ms:
            return True
        for a, b in dialogue_regions_ms:
            if a <= t_ms <= b:
                return True
        return False

    num_mid = 0.0
    den_low = 0.0
    n_frames = 0
    for i in range(S.shape[1]):
        t_ms = float(times_ms[i])
        if not _in_dialogue(t_ms):
            continue
        e_low = float(np.mean(S[low, i] ** 2))
        e_mid = float(np.mean(S[mid, i] ** 2))
        num_mid += e_mid
        den_low += max(e_low, 1e-18)
        n_frames += 1

    if n_frames == 0:
        num_mid = float(np.mean(S[mid, :] ** 2))
        den_low = float(np.mean(np.maximum(S[low, :] ** 2, 1e-18)))
        n_frames = S.shape[1]

    ratio_db = float(10.0 * np.log10((num_mid / max(n_frames, 1)) / (den_low / max(n_frames, 1))))
    return ratio_db, True


def run_mix_qa(
    audio_path: Path,
    *,
    target_lufs: float = -16.0,
    lufs_tolerance: float = 1.0,
    true_peak_max_dbfs: float = -1.0,
    plr_min: float = 6.0,
    plr_max: float = 14.0,
    intelligibility_min_db: float = 6.0,
    max_silence_gap_sec: float = 4.0,
    max_duration_drift_sec: float = 2.0,
    max_clip_samples: int = 10,
    plan_duration_seconds: Optional[float] = None,
    dialogue_regions_ms: Optional[List[Tuple[int, int]]] = None,
    plan: Any = None,
) -> Dict[str, Any]:
    """
    Run all QA checks on a rendered master.

    Returns ``{"checks": [CheckResult, ...], "summary": {...}}`` and JSON-serializable values.
    """
    path = Path(audio_path)
    checks: List[CheckResult] = []

    if not path.is_file():
        checks.append(
            _check_result(
                "file_exists",
                passed=False,
                value=None,
                threshold="file must exist",
                severity="fail",
            )
        )
        return {"checks": checks, "summary": {"all_passed": False, "rendered_duration_sec": None}}

    y, sr = _load_audio(path)
    dur_sec = (float(len(y)) / float(sr)) if sr else 0.0
    il = _integrated_lufs(y, sr)
    peak_dbfs = _sample_peak_dbfs(y)
    plr = _plr_estimate(peak_dbfs, il)
    clips = _clip_count(y)
    gap_ms = _longest_silence_gap_ms(y, sr)
    ratio_db, _ok = _band_ratio_db_dialogue(y, sr, dialogue_regions_ms)

    lufs_ok = abs(il - target_lufs) <= lufs_tolerance
    checks.append(
        _check_result(
            "loudness_lufs",
            passed=lufs_ok,
            value=round(il, 2),
            threshold=f"{target_lufs:.1f} ± {lufs_tolerance:.1f} LUFS",
            severity="warn" if not lufs_ok else "info",
        )
    )

    tp_ok = peak_dbfs <= true_peak_max_dbfs
    checks.append(
        _check_result(
            "true_peak_dbfs",
            passed=tp_ok,
            value=round(peak_dbfs, 2),
            threshold=f"≤ {true_peak_max_dbfs:.1f} dBFS",
            severity="warn" if not tp_ok else "info",
        )
    )

    plr_ok = plr_min <= plr <= plr_max
    checks.append(
        _check_result(
            "dynamic_range_plr",
            passed=plr_ok,
            value=round(plr, 2),
            threshold=f"{plr_min:.0f}–{plr_max:.0f} LU (peak vs integrated)",
            severity="warn" if not plr_ok else "info",
        )
    )

    intel_ok = ratio_db >= intelligibility_min_db
    sev = "info" if intel_ok else "warn"
    checks.append(
        _check_result(
            "voice_band_intelligibility",
            passed=intel_ok,
            value=round(ratio_db, 2),
            threshold=f"mid/low ≥ {intelligibility_min_db:.0f} dB during dialogue",
            severity=sev,
        )
    )

    gap_ok = (gap_ms / 1000.0) <= max_silence_gap_sec
    checks.append(
        _check_result(
            "silence_gaps",
            passed=gap_ok,
            value=round(gap_ms / 1000.0, 3),
            threshold=f"max gap ≤ {max_silence_gap_sec:.0f}s",
            severity="warn" if not gap_ok else "info",
        )
    )

    drift = None
    drift_ok = True
    if plan_duration_seconds is not None and plan_duration_seconds > 0:
        drift = abs(dur_sec - float(plan_duration_seconds))
        drift_ok = drift < max_duration_drift_sec
        checks.append(
            _check_result(
                "duration_drift",
                passed=drift_ok,
                value=round(drift, 3) if drift is not None else None,
                threshold=f"< {max_duration_drift_sec:.0f}s vs plan",
                severity="warn" if not drift_ok else "info",
            )
        )

    clip_ok = clips < max_clip_samples
    checks.append(
        _check_result(
            "clip_count",
            passed=clip_ok,
            value=clips,
            threshold=f"< {max_clip_samples} samples at |x|≥0.999",
            severity="warn" if not clip_ok else "info",
        )
    )

    all_passed = all(c["passed"] for c in checks)

    summary = {
        "all_passed": all_passed,
        "rendered_duration_sec": round(dur_sec, 3),
        "integrated_lufs": round(il, 2),
        "true_peak_dbfs": round(peak_dbfs, 2),
        "plr_lu": round(plr, 2),
        "target_lufs": target_lufs,
    }
    return {"checks": checks, "summary": summary}


def qa_to_episode_metadata(qa: Dict[str, Any]) -> str:
    """JSON string for storage alongside episode/task metadata."""
    return json.dumps(qa, default=str)
