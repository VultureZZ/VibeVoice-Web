"""
Classify ad-scan segments: the LLM sometimes labels editorial blocks (e.g. "News Segment")
inside ad_segments; those should not be treated as commercial ads for UI or export.
Keep logic in sync with frontend/src/utils/adScanSegments.ts.
"""

from __future__ import annotations

from typing import Any

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
