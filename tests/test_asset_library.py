#!/usr/bin/env python3
"""Unit tests for app.services.asset_library."""

import sys
import unittest
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pydantic import ValidationError

from app.services.asset_library import Asset, AssetLibrary


def _write_minimal_wav(path: Path, duration_ms: int = 200) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        nframes = int(8000 * (duration_ms / 1000.0))
        wf.writeframes(b"\x00\x00" * nframes)


class TestAssetLibrary(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self.tmp = Path(tempfile.mkdtemp(prefix="asset_lib_"))

    def tearDown(self) -> None:
        import shutil

        if self.tmp.exists():
            shutil.rmtree(self.tmp, ignore_errors=True)

    def test_search_get_add(self) -> None:
        lib = AssetLibrary(self.tmp)
        wav_a = self.tmp / "a.wav"
        wav_b = self.tmp / "b.wav"
        _write_minimal_wav(wav_a, 300)
        _write_minimal_wav(wav_b, 500)

        id_a = lib.add_asset(
            wav_a,
            {
                "category": "music_bed",
                "genre_tags": ["news", "storytelling"],
                "mood_tags": ["neutral"],
                "intensity": 3,
                "source": "user_uploaded",
                "licensing": "test",
                "duration_ms": 300,
                "bpm": 90,
            },
        )
        id_b = lib.add_asset(
            wav_b,
            {
                "category": "music_bed",
                "genre_tags": ["true_crime"],
                "mood_tags": ["tense"],
                "intensity": 4,
                "source": "builtin",
                "licensing": "test",
                "duration_ms": 500,
                "bpm": 72,
            },
        )

        got = lib.get(id_a)
        self.assertEqual(got.asset_id, id_a)
        self.assertEqual(got.category, "music_bed")
        self.assertIn("news", got.genre_tags)

        news_beds = lib.search("music_bed", genre="news")
        self.assertEqual(len(news_beds), 1)
        self.assertEqual(news_beds[0].asset_id, id_a)

        tc = lib.search("music_bed", genre="true_crime", mood="tense")
        self.assertEqual(len(tc), 1)
        self.assertEqual(tc[0].asset_id, id_b)

        in_range = lib.search("music_bed", bpm_range=(70, 95))
        self.assertEqual(len(in_range), 2)

        short = lib.search("music_bed", max_duration_ms=350)
        self.assertEqual(len(short), 1)
        self.assertEqual(short[0].asset_id, id_a)

    def test_as_llm_catalog_excludes_paths(self) -> None:
        lib = AssetLibrary(self.tmp)
        wav = self.tmp / "x.wav"
        _write_minimal_wav(wav)
        lib.add_asset(
            wav,
            {
                "category": "sfx_impact",
                "genre_tags": ["comedy"],
                "mood_tags": ["playful"],
                "intensity": 2,
                "source": "user_uploaded",
                "licensing": "test",
                "duration_ms": 200,
            },
        )
        rows = lib.as_llm_catalog({"category": "sfx_impact"})
        self.assertEqual(len(rows), 1)
        self.assertNotIn("path", rows[0])
        self.assertIn("asset_id", rows[0])
        self.assertIn("genre_tags", rows[0])

    def test_duplicate_asset_id_rejected(self) -> None:
        lib = AssetLibrary(self.tmp)
        wav = self.tmp / "d.wav"
        _write_minimal_wav(wav)
        meta = {
            "asset_id": "fixed-id-1",
            "category": "foley",
            "genre_tags": ["storytelling"],
            "mood_tags": ["neutral"],
            "intensity": 2,
            "source": "user_uploaded",
            "licensing": "test",
            "duration_ms": 200,
        }
        lib.add_asset(wav, dict(meta))
        with self.assertRaises(ValueError):
            lib.add_asset(wav, dict(meta))

    def test_asset_model_validation(self) -> None:
        with self.assertRaises(ValidationError):
            Asset(
                asset_id="x",
                path="music/beds/news/x.wav",
                category="music_bed",
                genre_tags=["news"],
                mood_tags=[],
                duration_ms=100,
                intensity=6,
                source="user_uploaded",
                licensing="x",
                created_at="2026-01-01T00:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
