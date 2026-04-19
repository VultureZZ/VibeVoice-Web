"""
Word-level timing index for trigger_word resolution and Director context.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

_WS_RE = re.compile(r"\s+")


def normalize_word_token(word: str) -> str:
    """Lowercase alphanumerics for fuzzy trigger matching."""
    return re.sub(r"[^a-z0-9'-]+", "", (word or "").lower())


def words_from_segment(
    seg: Dict[str, Any],
    line_index: int,
    speaker: str,
) -> List[Dict[str, Any]]:
    """
    Build word rows from a WhisperX segment (seconds) or uniform split fallback.
    Each row: word, line_index, speaker, start_ms, end_ms.
    """
    out: List[Dict[str, Any]] = []
    raw_words = seg.get("words") or []
    if isinstance(raw_words, list) and raw_words:
        for w in raw_words:
            if not isinstance(w, dict):
                continue
            word = str(w.get("word", "")).strip()
            st = float(w.get("start", seg.get("start", 0.0)))
            en = float(w.get("end", st + 0.02))
            if not word:
                continue
            out.append(
                {
                    "word": word,
                    "line_index": line_index,
                    "speaker": speaker,
                    "start_ms": int(max(0.0, st) * 1000.0),
                    "end_ms": int(max(st, en) * 1000.0),
                }
            )
        return out

    text = str(seg.get("text", "")).strip()
    tokens = _WS_RE.split(text) if text else []
    if not tokens:
        return []
    seg_start = float(seg.get("start", 0.0))
    seg_end = float(seg.get("end", seg_start + max(0.05, len(tokens) * 0.05)))
    dur = max(1e-6, seg_end - seg_start)
    step = dur / len(tokens)
    for i, tok in enumerate(tokens):
        st = seg_start + i * step
        en = seg_start + (i + 1) * step
        out.append(
            {
                "word": tok,
                "line_index": line_index,
                "speaker": speaker,
                "start_ms": int(st * 1000.0),
                "end_ms": int(en * 1000.0),
            }
        )
    return out


def build_fallback_word_index(
    dialogue: List[Dict[str, str]],
    timing_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Evenly-spaced words when alignment is unavailable."""
    out: List[Dict[str, Any]] = []
    for i, line in enumerate(dialogue):
        if i >= len(timing_rows):
            break
        row = timing_rows[i]
        st_ms = int(float(row.get("start_time_hint", 0.0)) * 1000.0)
        duration_ms = int(row.get("duration_ms") or 1000)
        text = line.get("text") or ""
        tokens = [t for t in _WS_RE.split(text.strip()) if t]
        if not tokens:
            continue
        step = duration_ms / len(tokens)
        for j, tok in enumerate(tokens):
            a = st_ms + int(j * step)
            b = st_ms + int((j + 0.95) * step)
            out.append(
                {
                    "word": tok,
                    "line_index": i,
                    "speaker": line.get("speaker", "Speaker 1"),
                    "start_ms": a,
                    "end_ms": b,
                }
            )
    return out


def compact_word_index_for_llm(entries: List[Dict[str, Any]], max_items: int = 1000) -> Dict[str, Any]:
    """Abbreviated word list for Director JSON context (token budget)."""
    trimmed = entries[:max_items]
    words = [
        {
            "w": str(e.get("word", ""))[:56],
            "i": int(e.get("line_index", 0)),
            "sp": str(e.get("speaker", ""))[:32],
            "a": int(e.get("start_ms", 0)),
            "b": int(e.get("end_ms", 0)),
        }
        for e in trimmed
    ]
    return {
        "truncated": len(entries) > max_items,
        "total_words": len(entries),
        "words": words,
    }
