"""
Classify ad-scan segments: the LLM sometimes mislabels main episode content as ads.
Keep logic in sync with frontend/src/utils/adScanSegments.ts (editorial substrings only;
dominant-label filtering is server-side).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from ..config import config

logger = logging.getLogger(__name__)

# Substrings in `label` that indicate main episode / editorial content, not a sponsor spot.
_EDITORIAL_LABEL_SUBSTRINGS: tuple[str, ...] = (
    "news segment",
    "main content",
    "editorial",
    "episode content",
    "story segment",
    "discussion segment",
    "interview segment",
    "host segment",
    "cold open",
)

_EDITORIAL_LABELS_EXACT: frozenset[str] = frozenset({"news", "editorial"})


def _merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not intervals:
        return []
    sorted_iv = sorted(intervals, key=lambda x: x[0])
    merged: list[tuple[float, float]] = [sorted_iv[0]]
    for a, b in sorted_iv[1:]:
        la, lb = merged[-1]
        if a <= lb + 0.001:
            merged[-1] = (la, max(lb, b))
        else:
            merged.append((a, b))
    return merged


def _merged_span_seconds(intervals: list[tuple[float, float]]) -> float:
    merged = _merge_intervals(intervals)
    return sum(max(0.0, b - a) for a, b in merged)


def filter_dominant_show_segments(
    segments: list[dict[str, Any]],
    total_duration_seconds: float,
    *,
    job_id: str | None = None,
    min_fraction: float | None = None,
) -> list[dict[str, Any]]:
    """
    If one label's merged coverage is >= min_fraction of the episode duration, treat that label as the
    show/network main content (not discrete ads) and remove all segments with that label.
    """
    if not segments or total_duration_seconds <= 0:
        return segments
    td = float(total_duration_seconds)
    frac = min_fraction if min_fraction is not None else float(
        getattr(config, "AD_SCAN_DOMINANT_LABEL_MIN_FRACTION", 0.45)
    )
    by_label: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for s in segments:
        if not isinstance(s, dict):
            continue
        lab = (s.get("label") or "").strip().lower()
        if not lab:
            continue
        try:
            a = float(s["start_seconds"])
            b = float(s["end_seconds"])
        except (KeyError, TypeError, ValueError):
            continue
        a = max(0.0, min(a, td))
        b = max(0.0, min(b, td))
        if b <= a:
            continue
        by_label[lab].append((a, b))

    best_label: str | None = None
    best_span = 0.0
    for lab, ivs in by_label.items():
        span = _merged_span_seconds(ivs)
        if span > best_span:
            best_span = span
            best_label = lab

    if best_label is None or best_span <= 0:
        return segments

    ratio = best_span / td
    if ratio < frac:
        return segments

    jid = job_id or "-"
    logger.info(
        "[ad-scan] job=%s dominant_show_filter label=%r merged_span_s=%.1f episode_s=%.1f ratio=%.2f min=%.2f",
        jid,
        best_label,
        best_span,
        td,
        ratio,
        frac,
    )
    return [
        s
        for s in segments
        if isinstance(s, dict) and (s.get("label") or "").strip().lower() != best_label
    ]


def is_commercial_ad_segment(segment: dict[str, Any]) -> bool:
    """Return True if this row should be cut as a sponsor/ad; False for editorial mislabels."""
    label = (segment.get("label") or "").strip().lower()
    if not label:
        return True
    if label in _EDITORIAL_LABELS_EXACT:
        return False
    for snippet in _EDITORIAL_LABEL_SUBSTRINGS:
        if snippet in label:
            return False
    return True


def commercial_ad_segments_only(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [s for s in segments if isinstance(s, dict) and is_commercial_ad_segment(s)]
