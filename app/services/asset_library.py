"""
Local podcast production asset library: indexed audio files under assets/library/.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

AssetCategory = Literal[
    "music_bed",
    "music_transition",
    "music_intro",
    "music_outro",
    "sfx_impact",
    "sfx_riser",
    "sfx_whoosh",
    "sfx_ambience",
    "sfx_laugh",
    "sfx_reveal",
    "foley",
    "voice_backchannel",
]

AssetSource = Literal["builtin", "ace_step_generated", "user_uploaded"]

# Slugs used in folder names and genre_tags
DEFAULT_GENRE_TAGS = ("tech_talk", "news", "storytelling", "true_crime", "comedy")


class LoopPoints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)


class Asset(BaseModel):
    """Single row in assets/library/index.json."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str
    path: str = Field(description="Path relative to library root")
    category: AssetCategory
    genre_tags: List[str] = Field(default_factory=list)
    mood_tags: List[str] = Field(default_factory=list)
    bpm: Optional[int] = None
    key: Optional[str] = None
    duration_ms: int = Field(ge=0)
    loop_points: Optional[LoopPoints] = None
    intensity: int = Field(ge=1, le=5)
    source: AssetSource
    licensing: str = ""
    created_at: str = Field(description="ISO8601 timestamp")


def default_library_root() -> Path:
    env = os.environ.get("ASSET_LIBRARY_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    # app/services/asset_library.py -> repo root
    return Path(__file__).resolve().parent.parent.parent / "assets" / "library"


# category -> (relative base path, requires_genre_subfolder)
_CATEGORY_LAYOUT: Dict[str, Tuple[str, bool]] = {
    "music_bed": ("music/beds", True),
    "music_intro": ("music/intros", True),
    "music_outro": ("music/outros", True),
    "music_transition": ("music/transitions", False),
    "sfx_impact": ("sfx/impacts", False),
    "sfx_riser": ("sfx/risers", False),
    "sfx_whoosh": ("sfx/whooshes", False),
    "sfx_ambience": ("sfx/ambiences", False),
    "sfx_laugh": ("sfx/laughs", False),
    "sfx_reveal": ("sfx/reveals", False),
    "foley": ("sfx/foley", False),
    "voice_backchannel": ("voice/backchannel", False),
}


def _normalize_tag(tag: str) -> str:
    return tag.strip().lower().replace(" ", "_").replace("-", "_")


def _primary_genre_folder(genre_tags: List[str]) -> str:
    if not genre_tags:
        return "general"
    return _normalize_tag(genre_tags[0])


def _destination_relative_path(
    category: AssetCategory,
    genre_tags: List[str],
    filename: str,
) -> str:
    base, needs_genre = _CATEGORY_LAYOUT[category]
    if needs_genre:
        g = _primary_genre_folder(genre_tags)
        return f"{base}/{g}/{filename}"
    return f"{base}/{filename}"


class AssetLibrary:
    """Filesystem-backed library with a single JSON index."""

    def __init__(self, root: Optional[Union[str, Path]] = None) -> None:
        self._root = Path(root) if root is not None else default_library_root()
        self._root.mkdir(parents=True, exist_ok=True)
        self._index_path = self._root / "index.json"
        self._assets: Dict[str, Asset] = {}
        self._load_index()

    @property
    def root(self) -> Path:
        return self._root

    @property
    def index_path(self) -> Path:
        return self._index_path

    def _load_index(self) -> None:
        self._assets = {}
        if not self._index_path.exists():
            self._save_index_unlocked()
            return
        raw = json.loads(self._index_path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                try:
                    a = Asset.model_validate(item)
                    self._assets[a.asset_id] = a
                except Exception as exc:
                    logger.warning("Skipping invalid index row: %s", exc)
        else:
            logger.warning("index.json is not a list; starting empty")

    def _save_index_unlocked(self) -> None:
        rows = [a.model_dump(mode="json") for a in sorted(self._assets.values(), key=lambda x: x.asset_id)]
        text = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
        tmp = self._index_path.with_suffix(".json.tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(self._index_path)

    def reload(self) -> None:
        """Reload index from disk (e.g. after external writes)."""
        self._load_index()

    def search(
        self,
        category: AssetCategory,
        *,
        genre: Optional[str] = None,
        mood: Optional[str] = None,
        min_duration_ms: Optional[int] = None,
        max_duration_ms: Optional[int] = None,
        bpm_range: Optional[Tuple[Optional[int], Optional[int]]] = None,
        intensity: Optional[int] = None,
        limit: int = 10,
    ) -> List[Asset]:
        gnorm = _normalize_tag(genre) if genre else None
        mnorm = _normalize_tag(mood) if mood else None
        bpm_lo: Optional[int] = None
        bpm_hi: Optional[int] = None
        if bpm_range is not None:
            bpm_lo, bpm_hi = bpm_range

        matches: List[Asset] = []
        for a in self._assets.values():
            if a.category != category:
                continue
            if gnorm and gnorm not in {_normalize_tag(t) for t in a.genre_tags}:
                continue
            if mnorm and mnorm not in {_normalize_tag(t) for t in a.mood_tags}:
                continue
            if min_duration_ms is not None and a.duration_ms < min_duration_ms:
                continue
            if max_duration_ms is not None and a.duration_ms > max_duration_ms:
                continue
            if bpm_range is not None and (bpm_lo is not None or bpm_hi is not None):
                if a.bpm is None:
                    continue
                if bpm_lo is not None and a.bpm < bpm_lo:
                    continue
                if bpm_hi is not None and a.bpm > bpm_hi:
                    continue
            if intensity is not None and a.intensity != intensity:
                continue
            matches.append(a)
        matches.sort(key=lambda x: x.asset_id)
        return matches[:limit]

    def get(self, asset_id: str) -> Asset:
        a = self._assets.get(asset_id)
        if a is None:
            raise KeyError(asset_id)
        return a

    def add_asset(
        self,
        file_path: Union[str, Path],
        metadata: Dict[str, Any],
    ) -> str:
        """
        Copy ``file_path`` into the library layout and append to the index.

        Required metadata keys: category, genre_tags (list), mood_tags (list),
        intensity (1-5), source, licensing. Optional: bpm, key, loop_points, duration_ms
        (if omitted, caller should compute duration before calling).
        """
        src = Path(file_path).expanduser().resolve()
        if not src.is_file():
            raise FileNotFoundError(str(src))

        category = metadata["category"]
        if category not in _CATEGORY_LAYOUT:
            raise ValueError(f"Unknown category: {category}")

        genre_tags = [_normalize_tag(t) for t in (metadata.get("genre_tags") or [])]
        mood_tags = [_normalize_tag(t) for t in (metadata.get("mood_tags") or [])]
        intensity = int(metadata.get("intensity", 3))
        source = metadata["source"]
        licensing = str(metadata.get("licensing") or "")

        duration_ms = metadata.get("duration_ms")
        if duration_ms is None:
            raise ValueError("duration_ms is required in metadata")
        duration_ms = int(duration_ms)

        ext = src.suffix.lower() or ".wav"
        if ext not in (".wav", ".mp3", ".flac", ".ogg", ".aiff", ".aif"):
            ext = ".wav"
        asset_id = str(metadata.get("asset_id") or uuid.uuid4())
        if asset_id in self._assets:
            raise ValueError(f"asset_id already exists: {asset_id}")
        filename = f"{asset_id}{ext}"
        rel = _destination_relative_path(category, genre_tags, filename)
        dest = self._root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

        lp = metadata.get("loop_points")
        loop_points: Optional[LoopPoints] = None
        if lp and isinstance(lp, dict):
            loop_points = LoopPoints.model_validate(lp)

        bpm = metadata.get("bpm")
        if bpm is not None:
            bpm = int(bpm)

        asset = Asset(
            asset_id=asset_id,
            path=rel.replace("\\", "/"),
            category=category,
            genre_tags=genre_tags,
            mood_tags=mood_tags,
            bpm=bpm,
            key=(str(metadata["key"]).strip() if metadata.get("key") else None),
            duration_ms=duration_ms,
            loop_points=loop_points,
            intensity=intensity,
            source=source,
            licensing=licensing,
            created_at=metadata.get("created_at")
            or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
        self._assets[asset_id] = asset
        self._save_index_unlocked()
        return asset_id

    def as_llm_catalog(
        self,
        filters: Optional[Dict[str, Any]] = None,
        *,
        limit: int = 80,
        genre_template: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compact JSON-safe rows for the Director LLM: no filesystem paths.

        When ``genre_template`` is set, :func:`filter_catalog_for_genre_template` narrows
        and orders rows (preferred tags, SFX allow-list).
        """
        filters = filters or {}
        category = filters.get("category")
        rows: List[Asset] = list(self._assets.values())
        if category:
            rows = [a for a in rows if a.category == category]
        genre = filters.get("genre")
        if genre:
            gn = _normalize_tag(str(genre))
            rows = [a for a in rows if gn in {_normalize_tag(t) for t in a.genre_tags}]
        mood = filters.get("mood")
        if mood:
            mn = _normalize_tag(str(mood))
            rows = [a for a in rows if mn in {_normalize_tag(t) for t in a.mood_tags}]

        rows.sort(key=lambda x: x.asset_id)
        out: List[Dict[str, Any]] = []
        for a in rows:
            out.append(
                {
                    "asset_id": a.asset_id,
                    "category": a.category,
                    "genre_tags": a.genre_tags,
                    "mood_tags": a.mood_tags,
                    "bpm": a.bpm,
                    "duration_ms": a.duration_ms,
                    "intensity": a.intensity,
                    "key": a.key,
                }
            )
        if genre_template is not None:
            from app.services.genre_templates import filter_catalog_for_genre_template

            return filter_catalog_for_genre_template(out, genre_template, limit=limit)
        return out[:limit]

    def resolve_path(self, asset_id: str) -> Path:
        """Absolute filesystem path for a library asset."""
        return (self._root / self.get(asset_id).path).resolve()

    def count_by_category_and_genre_tag(self, category: AssetCategory, genre_tag: str) -> int:
        gn = _normalize_tag(genre_tag)
        n = 0
        for a in self._assets.values():
            if a.category != category:
                continue
            if gn in {_normalize_tag(t) for t in a.genre_tags}:
                n += 1
        return n

    def ensure_layout_dirs(self) -> None:
        """Create expected subdirectories (idempotent)."""
        for cat, (base, needs_genre) in _CATEGORY_LAYOUT.items():
            if needs_genre:
                for g in DEFAULT_GENRE_TAGS:
                    (self._root / base / g).mkdir(parents=True, exist_ok=True)
            else:
                (self._root / base).mkdir(parents=True, exist_ok=True)
