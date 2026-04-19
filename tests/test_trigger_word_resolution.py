#!/usr/bin/env python3
"""Unit tests for trigger_word timing resolution."""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
for p in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from app.services.production_director import AssetRef, ProductionPlan, TimelineTrack, TrackEvent
from app.services.trigger_resolution import (
    apply_trigger_word_resolution,
    resolve_event_timing,
)
from app.services.word_index import compact_word_index_for_llm


def _plan_with_events(events: list) -> ProductionPlan:
    return ProductionPlan(
        episode_id="t",
        duration_target_seconds=120.0,
        genre="news",
        emotional_arc=[
            {"timestamp": 0.0, "valence": 0.0, "energy": 0.5},
            {"timestamp": 60.0, "valence": 0.0, "energy": 0.5},
            {"timestamp": 120.0, "valence": 0.0, "energy": 0.5},
        ],
        tracks=[
            TimelineTrack(
                track_id="sfx",
                track_role="sfx_impact",
                events=events,
            )
        ],
        voice_direction=[],
    )


class TestResolveImpact(unittest.TestCase):
    def test_impact_snaps_to_word_start(self):
        wi = [
            {"word": "Boom", "line_index": 0, "speaker": "Speaker 1", "start_ms": 5000, "end_ms": 5200},
        ]
        ev = TrackEvent(
            event_id="e1",
            start_ms=0,
            duration_ms=800,
            asset_ref=AssetRef(asset_id="x"),
            trigger_word="Boom",
        )
        s, d, _fi, _fo = resolve_event_timing(
            track_role="sfx_impact",
            event=ev,
            word_index=wi,
            timing_hints=[],
        )
        self.assertEqual(s, 5000)
        self.assertEqual(d, 800)


class TestResolveRiser(unittest.TestCase):
    def test_riser_ends_before_word(self):
        wi = [
            {"word": "secret", "line_index": 1, "speaker": "Speaker 1", "start_ms": 10000, "end_ms": 10400},
        ]
        ev = TrackEvent(
            event_id="e1",
            start_ms=8000,
            duration_ms=3000,
            asset_ref=AssetRef(asset_id="x"),
            fade_out_ms=50,
            trigger_word="secret",
        )
        s, d, _fi, fo = resolve_event_timing(
            track_role="sfx_riser",
            event=ev,
            word_index=wi,
            timing_hints=[],
        )
        self.assertEqual(s + d, 9900)
        self.assertGreaterEqual(fo, 50)


class TestResolveWhoosh(unittest.TestCase):
    def test_whoosh_centers_gap(self):
        hints = [
            {"line_index": 0, "start_ms": 0, "end_ms": 5000, "text": "a"},
            {"line_index": 1, "start_ms": 7000, "end_ms": 12000, "text": "Meanwhile b"},
        ]
        wi = [
            {"word": "Meanwhile", "line_index": 1, "speaker": "Speaker 1", "start_ms": 7100, "end_ms": 7200},
        ]
        ev = TrackEvent(
            event_id="e1",
            start_ms=5000,
            duration_ms=2000,
            asset_ref=AssetRef(asset_id="w"),
            trigger_word="Meanwhile",
        )
        s, d, _fi, _fo = resolve_event_timing(
            track_role="sfx_whoosh",
            event=ev,
            word_index=wi,
            timing_hints=hints,
        )
        center = s + d // 2
        self.assertAlmostEqual(center, 6000.0, delta=50)


class TestResolveBackchannel(unittest.TestCase):
    def test_backchannel_in_pause(self):
        wi = [
            {"word": "Long", "line_index": 0, "speaker": "Speaker 1", "start_ms": 0, "end_ms": 200},
            {"word": "pause", "line_index": 0, "speaker": "Speaker 1", "start_ms": 1000, "end_ms": 1300},
        ]
        ev = TrackEvent(
            event_id="e1",
            start_ms=400,
            duration_ms=400,
            asset_ref=AssetRef(asset_id="bc"),
            trigger_word="yeah",
            anchor_speaker="Speaker 1",
        )
        s, d, _fi, _fo = resolve_event_timing(
            track_role="voice_backchannel",
            event=ev,
            word_index=wi,
            timing_hints=[],
        )
        self.assertEqual(s, 350)
        self.assertEqual(d, 400)


class TestApplyPlan(unittest.TestCase):
    def test_apply_updates_track(self):
        ev = TrackEvent(
            event_id="e1",
            start_ms=0,
            duration_ms=500,
            asset_ref=AssetRef(asset_id="imp"),
            trigger_word="Hey",
        )
        plan = _plan_with_events([ev])
        wi = [
            {"word": "Hey", "line_index": 0, "speaker": "Speaker 1", "start_ms": 4242, "end_ms": 4300},
        ]
        out = apply_trigger_word_resolution(plan, wi, [])
        self.assertEqual(out.tracks[0].events[0].start_ms, 4242)


class TestCompactIndex(unittest.TestCase):
    def test_compact_truncates(self):
        rows = [{"word": "x", "line_index": 0, "speaker": "S", "start_ms": 0, "end_ms": 1} for _ in range(2000)]
        c = compact_word_index_for_llm(rows, max_items=100)
        self.assertTrue(c["truncated"])
        self.assertEqual(len(c["words"]), 100)


if __name__ == "__main__":
    unittest.main()
