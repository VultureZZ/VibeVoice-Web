"""Tests for GenreTemplate wiring: resolution, catalog filtering, mastering targets."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from app.services.genre_templates import (
    TEMPLATES,
    filter_catalog_for_genre_template,
    mastering_lufs,
    merge_voice_chain_params,
    resolve_genre_template,
)


class TestResolveGenreTemplate(unittest.TestCase):
    def test_explicit_production_genre_wins_over_legacy_style(self) -> None:
        t = resolve_genre_template(template_id="news", style="casual", metadata_genre=None)
        self.assertEqual(t.genre_id, "news")

    def test_style_alias_when_no_template_id(self) -> None:
        t = resolve_genre_template(template_id=None, style="tech_talk", metadata_genre=None)
        self.assertEqual(t.genre_id, "tech_talk")

    def test_metadata_genre_true_crime(self) -> None:
        t = resolve_genre_template(template_id=None, style=None, metadata_genre="True Crime")
        self.assertEqual(t.genre_id, "true_crime")


class TestMergeVoiceChainParams(unittest.TestCase):
    def test_absolute_keys_apply_after_defaults(self) -> None:
        p = merge_voice_chain_params({"reverb_room_size": 0.4})
        self.assertAlmostEqual(p["reverb_room_size"], 0.4)

    def test_delta_keys_do_not_erase_explicit_absolute_in_same_call(self) -> None:
        """Deltas adjust defaults; a later explicit merge layer can override (simulated)."""
        base = merge_voice_chain_params({"reverb_room_size_delta": 0.05})
        self.assertGreater(base["reverb_room_size"], 0.18)
        explicit = merge_voice_chain_params({"reverb_room_size": 0.12})
        self.assertAlmostEqual(explicit["reverb_room_size"], 0.12)


class TestFilterCatalogForGenreTemplate(unittest.TestCase):
    def test_as_llm_catalog_applies_template(self) -> None:
        from app.services.asset_library import AssetLibrary

        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / "stub.wav"
            sf.write(str(wav), np.zeros(800, dtype="float32"), 48000)
            lib = AssetLibrary(root=td)
            lib.add_asset(
                wav,
                {
                    "asset_id": "sfx_laugh_1",
                    "category": "sfx_laugh",
                    "genre_tags": [],
                    "mood_tags": [],
                    "intensity": 3,
                    "source": "user_uploaded",
                    "licensing": "test",
                    "duration_ms": 16,
                },
            )
            lib.add_asset(
                wav,
                {
                    "asset_id": "music_bed_1",
                    "category": "music_bed",
                    "genre_tags": ["comedy"],
                    "mood_tags": ["upbeat"],
                    "intensity": 3,
                    "source": "user_uploaded",
                    "licensing": "test",
                    "duration_ms": 2000,
                },
            )
            plain = lib.as_llm_catalog(limit=20, genre_template=None)
            news = lib.as_llm_catalog(limit=20, genre_template=TEMPLATES["news"])
            comedy = lib.as_llm_catalog(limit=20, genre_template=TEMPLATES["comedy"])
            plain_ids = {r["asset_id"] for r in plain}
            self.assertIn("sfx_laugh_1", plain_ids)
            news_ids = {r["asset_id"] for r in news}
            comedy_ids = {r["asset_id"] for r in comedy}
            self.assertNotIn("sfx_laugh_1", news_ids)
            self.assertIn("sfx_laugh_1", comedy_ids)

    def test_sfx_allow_list_differs_by_genre(self) -> None:
        rows = [
            {
                "asset_id": "l1",
                "category": "sfx_laugh",
                "genre_tags": [],
                "mood_tags": [],
            },
            {
                "asset_id": "m1",
                "category": "music_bed",
                "genre_tags": ["comedy"],
                "mood_tags": ["upbeat"],
            },
        ]
        comedy = TEMPLATES["comedy"]
        news = TEMPLATES["news"]
        c_out = filter_catalog_for_genre_template(rows, comedy, limit=20)
        n_out = filter_catalog_for_genre_template(rows, news, limit=20)
        c_ids = {r["asset_id"] for r in c_out}
        n_ids = {r["asset_id"] for r in n_out}
        self.assertIn("l1", c_ids)
        self.assertNotIn("l1", n_ids)
        self.assertIn("m1", n_ids)


class TestMasteringLufs(unittest.TestCase):
    def test_targets_within_tolerance(self) -> None:
        tol = 0.25
        for tid, tmpl in TEMPLATES.items():
            expected = float(tmpl.mastering_targets["lufs"])
            got = mastering_lufs(tmpl, "ignored_when_template_has_lufs")
            self.assertAlmostEqual(got, expected, delta=tol, msg=tid)


if __name__ == "__main__":
    unittest.main()
