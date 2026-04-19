"""
Resolve TrackEvent.trigger_word placements using WhisperX word index and timing hints.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.services.production_director import ProductionPlan, TimelineTrack, TrackEvent
from app.services.word_index import normalize_word_token

logger = logging.getLogger(__name__)


def _hint_start_ms(h: Dict[str, Any]) -> int:
    if h.get("start_ms") is not None:
        return int(h["start_ms"])
    st = h.get("start_time_hint")
    if st is not None:
        return int(float(st) * 1000.0)
    return 0


def _hints_by_line(timing_hints: Sequence[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for h in timing_hints:
        if not isinstance(h, dict):
            continue
        try:
            li = int(h.get("line_index", -1))
        except (TypeError, ValueError):
            continue
        if li >= 0:
            out[li] = h
    return out


def _find_word_matches(word_index: Sequence[Dict[str, Any]], trigger: str) -> List[Dict[str, Any]]:
    t = normalize_word_token(trigger)
    if not t:
        return []
    matches: List[Dict[str, Any]] = []
    for w in word_index:
        if normalize_word_token(str(w.get("word", ""))) == t:
            matches.append(w)
    return matches


def _pick_closest(matches: List[Dict[str, Any]], rough_ms: int) -> Optional[Dict[str, Any]]:
    if not matches:
        return None
    return min(matches, key=lambda m: abs(int(m.get("start_ms", 0)) - rough_ms))


def _gap_center_before_line(
    timing_hints: Sequence[Dict[str, Any]],
    line_index: int,
) -> Optional[int]:
    """Midpoint (ms) of silence between end of line_index-1 and start of line_index."""
    by_line = _hints_by_line(timing_hints)
    if line_index <= 0:
        return None
    prev_h = by_line.get(line_index - 1)
    cur_h = by_line.get(line_index)
    if not prev_h or not cur_h:
        return None
    try:
        prev_end = int(prev_h.get("end_ms", _hint_start_ms(prev_h) + 1000))
        cur_start = _hint_start_ms(cur_h)
    except (TypeError, ValueError):
        return None
    if cur_start <= prev_end:
        return (cur_start + prev_end) // 2
    return (cur_start + prev_end) // 2


def _line_text_contains_word(timing_hints: Sequence[Dict[str, Any]], line_index: int, trigger: str) -> bool:
    by_line = _hints_by_line(timing_hints)
    h = by_line.get(line_index)
    if not h:
        return False
    text = str(h.get("text", "") or "").lower()
    t = normalize_word_token(trigger)
    if not t:
        return False
    return t in re.sub(r"[^\w]+", "", text) or t in text.replace(" ", "")


def _infer_line_for_whoosh(
    word_index: Sequence[Dict[str, Any]],
    timing_hints: Sequence[Dict[str, Any]],
    trigger: str,
    rough_start_ms: int,
) -> Optional[int]:
    """Line index whose inter-line gap we center on (topic transition)."""
    matches = _find_word_matches(word_index, trigger)
    if matches:
        return int(matches[0].get("line_index", 0))
    # Fall back: line whose dialogue text contains the token
    by_line = _hints_by_line(timing_hints)
    for li in sorted(by_line.keys()):
        if _line_text_contains_word(timing_hints, li, trigger):
            return li
    # Nearest line by rough time
    best_li: Optional[int] = None
    best_d = 10**12
    for li, h in by_line.items():
        st = _hint_start_ms(h)
        d = abs(st - rough_start_ms)
        if d < best_d:
            best_d = d
            best_li = li
    return best_li


def _backchannel_start_ms(
    word_index: Sequence[Dict[str, Any]],
    anchor_speaker: str,
    duration_ms: int,
    rough_start_ms: int,
    pause_ms: int = 400,
    offset_into_pause_ms: int = 150,
) -> Optional[int]:
    """
    Find a pause >= pause_ms in anchor_speaker's speech; place clip at offset_into_pause_ms
    after pause start. Prefer pause nearest rough_start_ms.
    """
    sp = (anchor_speaker or "").strip()
    if not sp:
        return None
    by_line: Dict[int, List[Dict[str, Any]]] = {}
    for w in word_index:
        if str(w.get("speaker", "")).strip() != sp:
            continue
        li = int(w.get("line_index", 0))
        by_line.setdefault(li, []).append(w)

    candidates: List[int] = []
    for _li, words in by_line.items():
        arr = sorted(words, key=lambda x: int(x.get("start_ms", 0)))
        for i in range(len(arr) - 1):
            gap = int(arr[i + 1]["start_ms"]) - int(arr[i]["end_ms"])
            if gap >= pause_ms:
                start = int(arr[i]["end_ms"]) + offset_into_pause_ms
                if start + duration_ms <= int(arr[i + 1]["start_ms"]):
                    candidates.append(start)
    if not candidates:
        return None
    return min(candidates, key=lambda s: abs(s - rough_start_ms))


def resolve_event_timing(
    *,
    track_role: str,
    event: TrackEvent,
    word_index: Sequence[Dict[str, Any]],
    timing_hints: Sequence[Dict[str, Any]],
) -> Tuple[int, int, int, int]:
    """
    Returns (start_ms, duration_ms, fade_in_ms, fade_out_ms) after trigger resolution.
    """
    tw = (event.trigger_word or "").strip()
    rough_s = int(event.start_ms)
    dur = max(1, int(event.duration_ms))
    fi = int(event.fade_in_ms)
    fo = int(event.fade_out_ms)

    if not tw:
        return rough_s, dur, fi, fo

    if track_role == "sfx_impact":
        m = _pick_closest(_find_word_matches(word_index, tw), rough_s)
        if m:
            ns = int(m["start_ms"])
            return ns, dur, fi, fo
        logger.warning("sfx_impact: no word match for trigger %r", tw)
        return rough_s, dur, fi, fo

    if track_role == "sfx_riser":
        matches = _find_word_matches(word_index, tw)
        m = _pick_closest(matches, rough_s + dur // 2)
        if m:
            wstart = int(m["start_ms"])
            end_ms = max(0, wstart - 100)
            start_ms = max(0, end_ms - dur)
            nfo = max(fo, min(350, dur // 3))
            return start_ms, end_ms - start_ms, fi, nfo
        logger.warning("sfx_riser: no word match for trigger %r", tw)
        return rough_s, dur, fi, fo

    if track_role == "sfx_whoosh":
        li = _infer_line_for_whoosh(word_index, timing_hints, tw, rough_s)
        if li is not None:
            gap_line = max(1, li)
            center = _gap_center_before_line(timing_hints, gap_line)
            if center is not None:
                start_ms = max(0, center - dur // 2)
                return start_ms, dur, fi, fo
        logger.warning("sfx_whoosh: could not resolve gap for trigger %r", tw)
        return rough_s, dur, fi, fo

    if track_role == "voice_backchannel":
        anchor = (getattr(event, "anchor_speaker", None) or "").strip()
        placed = _backchannel_start_ms(word_index, anchor, dur, rough_s)
        if placed is not None:
            return placed, dur, fi, fo
        logger.warning("voice_backchannel: no pause for anchor %r; using rough start", anchor)
        return rough_s, dur, fi, fo

    return rough_s, dur, fi, fo


def apply_trigger_word_resolution(
    plan: ProductionPlan,
    word_index: Optional[Sequence[Dict[str, Any]]],
    timing_hints: Optional[Sequence[Dict[str, Any]]],
) -> ProductionPlan:
    if not word_index:
        return plan
    hints: List[Dict[str, Any]] = list(timing_hints or [])
    new_tracks: List[TimelineTrack] = []
    for tr in plan.tracks:
        role = str(tr.track_role)
        if role not in (
            "sfx_impact",
            "sfx_riser",
            "sfx_whoosh",
            "voice_backchannel",
        ):
            new_tracks.append(tr)
            continue
        new_events: List[TrackEvent] = []
        for ev in tr.events:
            if not ev.trigger_word:
                new_events.append(ev)
                continue
            s, d, fi, fo = resolve_event_timing(
                track_role=role,
                event=ev,
                word_index=word_index,
                timing_hints=hints,
            )
            new_events.append(
                ev.model_copy(
                    update={
                        "start_ms": s,
                        "duration_ms": max(1, d),
                        "fade_in_ms": fi,
                        "fade_out_ms": fo,
                    }
                )
            )
        new_tracks.append(tr.model_copy(update={"events": new_events}))
    return plan.model_copy(update={"tracks": new_tracks})
