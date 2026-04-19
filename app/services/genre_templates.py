"""
First-class genre templates driving Director prompts, library filtering, generation, and mastering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set

# All SFX-ish categories that can be toggled per template
def _normalize_tag(t: str) -> str:
    return t.strip().lower().replace(" ", "_").replace("-", "_")


_ALL_SFX_CATEGORIES: FrozenSet[str] = frozenset(
    {
        "sfx_impact",
        "sfx_riser",
        "sfx_whoosh",
        "sfx_ambience",
        "sfx_laugh",
        "sfx_reveal",
        "foley",
    }
)


@dataclass(frozen=True)
class GenreTemplate:
    """Single production genre profile."""

    genre_id: str
    display_name: str
    director_rules: Dict[str, Any]
    """music_density, sfx_density, pacing_notes, reverb_style, example_patterns (list of dicts)."""
    voice_chain_overrides: Dict[str, float]
    """Absolute or *_delta keys merged with defaults in ProductionMixer (see merge_voice_chain_params)."""
    library_filters: Dict[str, Any]
    """preferred_genre_tags, preferred_mood_tags, exclude_categories (optional lists)."""
    generation_prompt_modifiers: Dict[str, str]
    """prefix, suffix, and optional keys music_prefix, sfx_prefix, music_suffix, sfx_suffix."""
    mastering_targets: Dict[str, float]
    """lufs (integrated), peak_db (limiter ceiling), dynamic_range (LU, informational)."""
    sfx_enabled_categories: Optional[FrozenSet[str]] = None
    """None = all SFX categories allowed; otherwise intersection with library rows."""


def merge_voice_chain_params(overrides: Dict[str, float]) -> Dict[str, float]:
    """Merge template overrides/deltas onto default per-line voice chain parameters."""
    defaults = {
        "highpass_hz": 80.0,
        "noise_gate_threshold_db": -50.0,
        "noise_gate_ratio": 3.0,
        "compressor_threshold_db": -18.0,
        "compressor_ratio": 3.0,
        "compressor_attack_ms": 5.0,
        "compressor_release_ms": 120.0,
        "peak_filter_gain_db": 2.5,
        "peak_filter_q": 0.8,
        "reverb_room_size": 0.18,
        "reverb_wet_level": 0.06,
        "master_compressor_threshold_db": -14.0,
        "master_compressor_ratio": 2.0,
        "master_compressor_attack_ms": 10.0,
        "master_compressor_release_ms": 150.0,
        "master_limiter_threshold_db": -1.0,
    }
    out = dict(defaults)
    for k, v in overrides.items():
        if k.endswith("_delta"):
            base_key = k[:-6]
            if base_key in out:
                out[base_key] = float(out[base_key]) + float(v)
        else:
            out[k] = float(v)
    return out


_LUFS_FALLBACK: Dict[str, float] = {
    "true_crime": -18.0,
    "true crime": -18.0,
    "news": -16.0,
    "comedy": -15.0,
}


def mastering_lufs(template: Optional[GenreTemplate], plan_genre: str) -> float:
    """Integrated loudness target: template mastering_targets.lufs, else legacy plan genre string."""
    if template is not None and "lufs" in template.mastering_targets:
        return float(template.mastering_targets["lufs"])
    g = (plan_genre or "").strip().lower()
    return _LUFS_FALLBACK.get(g, -16.0)


def mastering_peak_db(template: Optional[GenreTemplate]) -> float:
    if template is not None and "peak_db" in template.mastering_targets:
        return float(template.mastering_targets["peak_db"])
    return -1.0


TEMPLATES: Dict[str, GenreTemplate] = {
    "tech_talk": GenreTemplate(
        genre_id="tech_talk",
        display_name="Tech Talk",
        director_rules={
            "music_density": "low",
            "sfx_density": "low",
            "pacing_notes": (
                "Clear explanations; music only under transitions; avoid clutter; "
                "emphasize product names with light SFX, not wall-to-wall beds."
            ),
            "reverb_style": "dry booth, subtle short plate on host only",
            "example_patterns": [
                {
                    "episode_id": "fewshot-tt-1",
                    "duration_target_seconds": 600.0,
                    "genre": "Tech Talk",
                    "tracks_hint": [
                        {"track_role": "voice_main", "note": "confident, concise"},
                        {"track_role": "music_transition", "note": "single clean bridge between sections"},
                    ],
                },
            ],
        },
        voice_chain_overrides={
            "reverb_room_size_delta": -0.04,
            "reverb_wet_level_delta": -0.02,
            "compressor_threshold_db": -17.0,
        },
        library_filters={
            "preferred_genre_tags": ["tech_talk", "news"],
            "preferred_mood_tags": ["neutral", "focused", "technical"],
            "exclude_categories": [],
        },
        generation_prompt_modifiers={
            "prefix": "clean, modern, minimal —",
            "suffix": "— tight mix, no vocals in bed",
            "music_prefix": "sparse electronic, subtle pulse —",
            "sfx_prefix": "short, precise, UI-adjacent —",
        },
        mastering_targets={"lufs": -16.0, "peak_db": -1.0, "dynamic_range": 9.0},
        sfx_enabled_categories=_ALL_SFX_CATEGORIES - frozenset({"sfx_laugh"}),
    ),
    "news": GenreTemplate(
        genre_id="news",
        display_name="News",
        director_rules={
            "music_density": "low",
            "sfx_density": "low",
            "pacing_notes": (
                "NPR-style clarity: music sits under narration; hard commits on facts; "
                "light room tone; avoid sensational stings."
            ),
            "reverb_style": "dry booth, short plate under VO only for scene recall",
            "example_patterns": [
                {
                    "episode_id": "fewshot-news-1",
                    "duration_target_seconds": 600.0,
                    "genre": "News",
                    "tracks_hint": [
                        {"track_role": "music_bed", "note": "sparse piano under host intro only"},
                    ],
                },
            ],
        },
        voice_chain_overrides={
            "reverb_room_size_delta": -0.05,
            "noise_gate_threshold_db": -48.0,
        },
        library_filters={
            "preferred_genre_tags": ["news", "storytelling"],
            "preferred_mood_tags": ["neutral", "serious", "journalistic"],
            "exclude_categories": [],
        },
        generation_prompt_modifiers={
            "prefix": "neutral, authoritative, broadcast-safe —",
            "suffix": "— no comedy cues, restrained dynamics",
            "music_prefix": "light underscore, acoustic or piano —",
        },
        mastering_targets={"lufs": -16.0, "peak_db": -1.0, "dynamic_range": 8.5},
        sfx_enabled_categories=_ALL_SFX_CATEGORIES - frozenset({"sfx_laugh"}),
    ),
    "storytelling": GenreTemplate(
        genre_id="storytelling",
        display_name="Storytelling",
        director_rules={
            "music_density": "medium",
            "sfx_density": "medium",
            "pacing_notes": (
                "Narrative arc; music supports emotional beats; SFX for scene changes; "
                "leave space for VO."
            ),
            "reverb_style": "medium plate on narration; warm room on dialogue",
            "example_patterns": [
                {
                    "episode_id": "fewshot-st-1",
                    "duration_target_seconds": 900.0,
                    "genre": "Storytelling",
                    "tracks_hint": [
                        {"track_role": "music_bed", "note": "motif returns each act"},
                    ],
                },
            ],
        },
        voice_chain_overrides={
            "reverb_room_size": 0.22,
            "reverb_wet_level": 0.07,
        },
        library_filters={
            "preferred_genre_tags": ["storytelling", "news", "comedy"],
            "preferred_mood_tags": ["warm", "cinematic", "hopeful"],
            "exclude_categories": [],
        },
        generation_prompt_modifiers={
            "prefix": "cinematic, emotional, narrative —",
            "suffix": "— leave headroom for voice",
            "music_prefix": "orchestral-lite or acoustic bed —",
        },
        mastering_targets={"lufs": -16.0, "peak_db": -1.0, "dynamic_range": 9.5},
        sfx_enabled_categories=_ALL_SFX_CATEGORIES,
    ),
    "true_crime": GenreTemplate(
        genre_id="true_crime",
        display_name="True Crime",
        director_rules={
            "music_density": "medium",
            "sfx_density": "high",
            "pacing_notes": (
                "Ira Glass-style scoring: restrained motifs; slow reveals; low drones; "
                "sting only on turns; avoid laughs."
            ),
            "reverb_style": "dark plate on narration; dialogue drier",
            "example_patterns": [
                {
                    "episode_id": "fewshot-tc-1",
                    "duration_target_seconds": 1200.0,
                    "genre": "True Crime",
                    "tracks_hint": [
                        {"track_role": "music_bed", "note": "pulse at 72 BPM, minor"},
                    ],
                },
            ],
        },
        voice_chain_overrides={
            "reverb_room_size_delta": 0.08,
            "reverb_wet_level_delta": 0.03,
            "compressor_threshold_db": -19.0,
        },
        library_filters={
            "preferred_genre_tags": ["true_crime", "storytelling"],
            "preferred_mood_tags": ["dark", "tense", "minimal"],
            "exclude_categories": [],
        },
        generation_prompt_modifiers={
            "prefix": "dark, tense, minimal —",
            "suffix": "— no crowd laughter, no upbeat grooves",
            "music_prefix": "low drone, minor, slow —",
            "sfx_prefix": "subtle, ominous, short —",
        },
        mastering_targets={"lufs": -18.0, "peak_db": -1.0, "dynamic_range": 10.0},
        sfx_enabled_categories=_ALL_SFX_CATEGORIES - frozenset({"sfx_laugh"}),
    ),
    "comedy": GenreTemplate(
        genre_id="comedy",
        display_name="Comedy",
        director_rules={
            "music_density": "medium",
            "sfx_density": "medium",
            "pacing_notes": (
                "Snappy edits; music hits punchlines; rapid banter; "
                "foley sparingly; laughs allowed."
            ),
            "reverb_style": "bright room, short decay",
            "example_patterns": [
                {
                    "episode_id": "fewshot-com-1",
                    "duration_target_seconds": 540.0,
                    "genre": "Comedy",
                    "tracks_hint": [
                        {"track_role": "voice_main", "note": "double-host ping-pong"},
                    ],
                },
            ],
        },
        voice_chain_overrides={
            "reverb_room_size_delta": -0.06,
            "reverb_wet_level_delta": -0.03,
            "peak_filter_gain_db": 2.0,
        },
        library_filters={
            "preferred_genre_tags": ["comedy", "storytelling"],
            "preferred_mood_tags": ["playful", "upbeat", "bright"],
            "exclude_categories": [],
        },
        generation_prompt_modifiers={
            "prefix": "playful, bouncy, upbeat —",
            "suffix": "— tight timing, punchy transients",
            "music_prefix": "funk or light band bed —",
            "sfx_prefix": "cartoon-adjacent ok —",
        },
        mastering_targets={"lufs": -15.0, "peak_db": -0.8, "dynamic_range": 7.5},
        sfx_enabled_categories=_ALL_SFX_CATEGORIES,
    ),
}


STYLE_TO_TEMPLATE_ID: Dict[str, str] = {
    "tech_talk": "tech_talk",
    "casual": "comedy",
    "news": "news",
    "storytelling": "storytelling",
}


def resolve_genre_template(
    *,
    template_id: Optional[str] = None,
    style: Optional[str] = None,
    metadata_genre: Optional[str] = None,
) -> GenreTemplate:
    """
    Resolve API inputs to a template.

    Priority: explicit ``template_id`` → map ``style`` → normalize ``metadata_genre``
    (e.g. 'True Crime') → default storytelling.
    """
    if template_id:
        tid = _normalize_id(template_id)
        if tid in TEMPLATES:
            return TEMPLATES[tid]
    if style:
        sid = _normalize_id(style)
        if sid in STYLE_TO_TEMPLATE_ID:
            return TEMPLATES[STYLE_TO_TEMPLATE_ID[sid]]
    if metadata_genre:
        g = _normalize_id(metadata_genre)
        # "true crime", "True Crime"
        if "crime" in g or g == "true_crime":
            return TEMPLATES["true_crime"]
        if "news" in g:
            return TEMPLATES["news"]
        if "comedy" in g or "humor" in g:
            return TEMPLATES["comedy"]
        if "tech" in g:
            return TEMPLATES["tech_talk"]
        if "story" in g:
            return TEMPLATES["storytelling"]
        for tid, t in TEMPLATES.items():
            if tid == g or _normalize_id(t.display_name) == g:
                return t
    return TEMPLATES["storytelling"]


def _normalize_id(s: str) -> str:
    return s.strip().lower().replace(" ", "_").replace("-", "_")


def filter_catalog_for_genre_template(
    rows: List[Dict[str, Any]],
    template: Optional[GenreTemplate],
    *,
    limit: int,
) -> List[Dict[str, Any]]:
    """Apply library_filters + SFX category allow-list; prefer tag matches first."""
    if not template:
        return rows[:limit]
    lf = template.library_filters
    excl: Set[str] = set(lf.get("exclude_categories") or [])
    pref_g = {_normalize_tag(str(t)) for t in (lf.get("preferred_genre_tags") or [])}
    pref_m = {_normalize_tag(str(t)) for t in (lf.get("preferred_mood_tags") or [])}
    sfx_allow = template.sfx_enabled_categories

    def _tag_sets(row: Dict[str, Any]) -> tuple:
        gt = {_normalize_tag(t) for t in (row.get("genre_tags") or [])}
        mt = {_normalize_tag(t) for t in (row.get("mood_tags") or [])}
        cat = str(row.get("category") or "")
        return gt, mt, cat

    filtered: List[Dict[str, Any]] = []
    for row in rows:
        cat = str(row.get("category") or "")
        if cat in excl:
            continue
        if sfx_allow is not None and (cat.startswith("sfx") or cat == "foley"):
            if cat not in sfx_allow:
                continue
        filtered.append(row)

    def _score(row: Dict[str, Any]) -> int:
        gt, mt, _ = _tag_sets(row)
        sc = 0
        if pref_g and gt & pref_g:
            sc += 3
        if pref_m and mt & pref_m:
            sc += 2
        return sc

    if pref_g or pref_m:
        filtered.sort(key=lambda r: (-_score(r), str(r.get("asset_id", ""))))
    out = filtered[:limit]
    if len(out) < min(8, limit) and rows:
        # Fallback: do not starve the Director — top up from unfiltered (respecting sfx allow)
        seen = {r.get("asset_id") for r in out}
        for row in rows:
            if len(out) >= limit:
                break
            aid = row.get("asset_id")
            if aid in seen:
                continue
            cat = str(row.get("category") or "")
            if sfx_allow is not None and (cat.startswith("sfx") or cat == "foley"):
                if cat not in sfx_allow:
                    continue
            if cat in excl:
                continue
            out.append(row)
            seen.add(aid)
    return out[:limit]


def apply_generation_prompt_modifiers(
    prompt: str,
    category: str,
    template: Optional[GenreTemplate],
) -> str:
    """Prefix/suffix ACE-Step / Stable Audio prompts from template."""
    if not template:
        return prompt.strip()
    m = template.generation_prompt_modifiers
    p = (m.get("prefix") or "").strip()
    s = (m.get("suffix") or "").strip()
    cat = (category or "").strip()
    mp = (m.get("music_prefix") or m.get("music") or "").strip()
    sp = (m.get("sfx_prefix") or m.get("sfx") or "").strip()
    mid = ""
    if cat.startswith("music") and mp:
        mid = mp + " "
    elif (cat.startswith("sfx") or cat == "foley") and sp:
        mid = sp + " "
    core = prompt.strip()
    parts = [x for x in (p, mid + core, s) if x]
    return " ".join(parts).strip()


__all__ = [
    "GenreTemplate",
    "TEMPLATES",
    "STYLE_TO_TEMPLATE_ID",
    "apply_generation_prompt_modifiers",
    "filter_catalog_for_genre_template",
    "mastering_lufs",
    "mastering_peak_db",
    "merge_voice_chain_params",
    "resolve_genre_template",
]
