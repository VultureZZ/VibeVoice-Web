"""
Starter ACE-Step caption prompts for hydrating the local asset library.

Each entry targets a category + primary genre tag. Used by scripts/hydrate_library.py.
"""

from __future__ import annotations

from typing import List, TypedDict


class SeedSpec(TypedDict, total=False):
    """Parameters for one ACE-Step generation."""

    category: str
    primary_genre_tag: str
    caption: str
    duration_seconds: float
    instrumental: bool
    bpm: int
    keyscale: str


# ~20 seeds across music beds, transitions, intros/outros, and SFX-styled instrumental hits.
ACE_STEP_LIBRARY_SEEDS: List[SeedSpec] = [
    {
        "category": "music_bed",
        "primary_genre_tag": "news",
        "caption": "Sparse neutral newsroom underscore, piano and soft strings, no drums, NPR documentary tone",
        "duration_seconds": 45.0,
        "instrumental": True,
        "bpm": 82,
        "keyscale": "D Major",
    },
    {
        "category": "music_bed",
        "primary_genre_tag": "true_crime",
        "caption": "Low pulsing minor synth drone, tense but restrained, true crime podcast bed, no percussion",
        "duration_seconds": 60.0,
        "instrumental": True,
        "bpm": 72,
        "keyscale": "C minor",
    },
    {
        "category": "music_bed",
        "primary_genre_tag": "comedy",
        "caption": "Light quirky pizzicato and brushed drums, playful podcast bed, bright mix",
        "duration_seconds": 40.0,
        "instrumental": True,
        "bpm": 110,
        "keyscale": "F Major",
    },
    {
        "category": "music_bed",
        "primary_genre_tag": "storytelling",
        "caption": "Warm acoustic guitar and soft pads, narrative storytelling bed, gentle dynamics",
        "duration_seconds": 55.0,
        "instrumental": True,
        "bpm": 76,
        "keyscale": "G Major",
    },
    {
        "category": "music_bed",
        "primary_genre_tag": "tech_talk",
        "caption": "Clean arpeggiated synths and subtle bass, modern tech podcast underscore, minimal",
        "duration_seconds": 50.0,
        "instrumental": True,
        "bpm": 92,
        "keyscale": "A minor",
    },
    {
        "category": "music_transition",
        "primary_genre_tag": "news",
        "caption": "Short bright harmonic sting, 2 seconds, broadcast transition, no vocal",
        "duration_seconds": 3.0,
        "instrumental": True,
        "bpm": 96,
        "keyscale": "C Major",
    },
    {
        "category": "music_transition",
        "primary_genre_tag": "true_crime",
        "caption": "Dark low orchestral hit with reversed swell, 2.5 seconds, act break sting",
        "duration_seconds": 3.5,
        "instrumental": True,
        "bpm": 70,
        "keyscale": "D minor",
    },
    {
        "category": "music_transition",
        "primary_genre_tag": "comedy",
        "caption": "Brassy comedic bumper, punchy and short, cartoonish but not childish",
        "duration_seconds": 2.5,
        "instrumental": True,
        "bpm": 120,
        "keyscale": "Bb Major",
    },
    {
        "category": "music_intro",
        "primary_genre_tag": "news",
        "caption": "Opening theme, confident piano motif with light percussion, 12 seconds, fades to bed",
        "duration_seconds": 12.0,
        "instrumental": True,
        "bpm": 88,
        "keyscale": "E Major",
    },
    {
        "category": "music_intro",
        "primary_genre_tag": "storytelling",
        "caption": "Cinematic intro swell, strings and soft choir pad, emotional but not epic",
        "duration_seconds": 15.0,
        "instrumental": True,
        "bpm": 68,
        "keyscale": "Eb Major",
    },
    {
        "category": "music_outro",
        "primary_genre_tag": "news",
        "caption": "Closing theme resolve, warm strings and gentle guitar, 10 seconds, soft ending",
        "duration_seconds": 10.0,
        "instrumental": True,
        "bpm": 84,
        "keyscale": "D Major",
    },
    {
        "category": "music_outro",
        "primary_genre_tag": "true_crime",
        "caption": "Somber outro pad with low piano, unresolved minor chord, 12 seconds",
        "duration_seconds": 12.0,
        "instrumental": True,
        "bpm": 66,
        "keyscale": "A minor",
    },
    {
        "category": "sfx_impact",
        "primary_genre_tag": "storytelling",
        "caption": "Single deep cinematic impact, no tail music, one hit only, stereo",
        "duration_seconds": 2.0,
        "instrumental": True,
        "bpm": 60,
        "keyscale": "C",
    },
    {
        "category": "sfx_riser",
        "primary_genre_tag": "true_crime",
        "caption": "Tension riser white noise and string slide building 4 seconds, podcast reveal",
        "duration_seconds": 4.5,
        "instrumental": True,
        "bpm": 72,
        "keyscale": "E minor",
    },
    {
        "category": "sfx_whoosh",
        "primary_genre_tag": "comedy",
        "caption": "Fast airy whoosh with cartoonish tail, transition sweep, no melody",
        "duration_seconds": 1.5,
        "instrumental": True,
        "bpm": 100,
        "keyscale": "F",
    },
    {
        "category": "sfx_ambience",
        "primary_genre_tag": "true_crime",
        "caption": "Rain and distant thunder room tone loop, subtle low rumble, no musical pitch",
        "duration_seconds": 30.0,
        "instrumental": True,
        "bpm": 0,
        "keyscale": "",
    },
    {
        "category": "sfx_ambience",
        "primary_genre_tag": "news",
        "caption": "Quiet office air and keyboard clicks bed, very low level ambience",
        "duration_seconds": 25.0,
        "instrumental": True,
        "bpm": 0,
        "keyscale": "",
    },
    {
        "category": "sfx_laugh",
        "primary_genre_tag": "comedy",
        "caption": "Small studio audience polite laugh swell, 3 seconds, dry room",
        "duration_seconds": 3.0,
        "instrumental": True,
        "bpm": 90,
        "keyscale": "G",
    },
    {
        "category": "foley",
        "primary_genre_tag": "storytelling",
        "caption": "Footsteps on wood floor with fabric rustle, foley only, no music",
        "duration_seconds": 4.0,
        "instrumental": True,
        "bpm": 0,
        "keyscale": "",
    },
    {
        "category": "music_intro",
        "primary_genre_tag": "tech_talk",
        "caption": "Synth pulse logo sting with subtle glitch accents, startup podcast intro 8 seconds",
        "duration_seconds": 8.0,
        "instrumental": True,
        "bpm": 100,
        "keyscale": "B minor",
    },
]


def seeds_for_category_and_genre(category: str, primary_genre_tag: str) -> List[SeedSpec]:
    """All seeds that match category and primary genre tag."""
    tag = primary_genre_tag.strip().lower().replace(" ", "_")
    return [s for s in ACE_STEP_LIBRARY_SEEDS if s.get("category") == category and s.get("primary_genre_tag") == tag]


def pick_seed_round_robin(category: str, primary_genre_tag: str, index: int) -> SeedSpec:
    """Choose a seed by cycling through matching seeds, or fall back to any category match."""
    pool = seeds_for_category_and_genre(category, primary_genre_tag)
    if not pool:
        pool = [s for s in ACE_STEP_LIBRARY_SEEDS if s.get("category") == category]
    if not pool:
        pool = ACE_STEP_LIBRARY_SEEDS
    return pool[index % len(pool)]
