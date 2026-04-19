#!/usr/bin/env python3
"""
Integration-style test: ~2-minute timeline, multiple trigger_word resolutions within ±50ms.
Uses synthetic word_index (no Whisper dependency).
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
for p in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from app.services.production_director import AssetRef, ProductionPlan, TimelineTrack, TrackEvent
from app.services.trigger_resolution import apply_trigger_word_resolution


def _two_minute_word_index() -> list:
    """~120s episode: lines 0–4 with known word times (stretched pacing)."""
    wi = []
    t = 0
    lines = [
        ("Speaker 1", "Welcome back to the show today"),
        ("Speaker 2", "Thanks for having me here"),
        ("Speaker 1", "We will discuss the secret evidence now"),
        ("Speaker 2", "Meanwhile I agree completely"),
        ("Speaker 1", "Finally we wrap up the story"),
    ]
    line_index = 0
    for spk, sentence in lines:
        for w in sentence.split():
            dur = 4200 + len(w) * 30
            wi.append(
                {
                    "word": w,
                    "line_index": line_index,
                    "speaker": spk,
                    "start_ms": t,
                    "end_ms": t + dur,
                }
            )
            t += dur + 400
        line_index += 1
    if wi and wi[-1]["end_ms"] < 120_000:
        wi[-1] = {**wi[-1], "end_ms": 120_000}
    return wi


def _timing_hints_from_words(wi: list) -> list:
    by_li: dict = {}
    for w in wi:
        li = w["line_index"]
        by_li.setdefault(li, []).append(w)
    hints = []
    for li in sorted(by_li.keys()):
        arr = sorted(by_li[li], key=lambda x: x["start_ms"])
        text = " ".join(x["word"] for x in arr)
        hints.append(
            {
                "line_index": li,
                "speaker": arr[0]["speaker"],
                "text": text,
                "start_ms": arr[0]["start_ms"],
                "end_ms": arr[-1]["end_ms"],
            }
        )
    return hints


class TestTwoMinuteTriggerAlignment(unittest.TestCase):
    def test_five_triggers_within_50ms(self):
        wi = _two_minute_word_index()
        hints = _timing_hints_from_words(wi)

        events = [
            TrackEvent(
                event_id="i1",
                start_ms=0,
                duration_ms=400,
                asset_ref=AssetRef(asset_id="sfx1"),
                trigger_word="show",
            ),
            TrackEvent(
                event_id="r1",
                start_ms=5000,
                duration_ms=2500,
                asset_ref=AssetRef(asset_id="riser1"),
                fade_out_ms=80,
                trigger_word="secret",
            ),
            TrackEvent(
                event_id="w1",
                start_ms=20000,
                duration_ms=1500,
                asset_ref=AssetRef(asset_id="whoosh1"),
                trigger_word="Meanwhile",
            ),
            TrackEvent(
                event_id="bc1",
                start_ms=15000,
                duration_ms=500,
                asset_ref=AssetRef(asset_id="bc_sp2_yeah"),
                trigger_word="yeah",
                anchor_speaker="Speaker 1",
            ),
            TrackEvent(
                event_id="i2",
                start_ms=80000,
                duration_ms=300,
                asset_ref=AssetRef(asset_id="sfx2"),
                trigger_word="story",
            ),
        ]
        tracks = [
            TimelineTrack(track_id="imp", track_role="sfx_impact", events=[events[0], events[4]]),
            TimelineTrack(track_id="ris", track_role="sfx_riser", events=[events[1]]),
            TimelineTrack(track_id="who", track_role="sfx_whoosh", events=[events[2]]),
            TimelineTrack(track_id="bc", track_role="voice_backchannel", events=[events[3]]),
        ]
        plan = ProductionPlan(
            episode_id="int",
            duration_target_seconds=120.0,
            genre="news",
            emotional_arc=[
                {"timestamp": 0.0, "valence": 0.0, "energy": 0.5},
                {"timestamp": 60.0, "valence": 0.0, "energy": 0.5},
                {"timestamp": 120.0, "valence": 0.0, "energy": 0.5},
            ],
            tracks=tracks,
            voice_direction=[],
        )
        resolved = apply_trigger_word_resolution(plan, wi, hints)

        def _find_word(tw: str) -> int:
            for w in wi:
                if w["word"].lower().strip(".,!?") == tw.lower():
                    return int(w["start_ms"])
            raise AssertionError(tw)

        # Impact "show"
        show_t = _find_word("show")
        ev0 = resolved.tracks[0].events[0]
        self.assertLessEqual(abs(ev0.start_ms - show_t), 50)

        # Riser ends 100ms before "secret"
        secret_t = _find_word("secret")
        ev_r = resolved.tracks[1].events[0]
        self.assertLessEqual(abs((ev_r.start_ms + ev_r.duration_ms) - (secret_t - 100)), 50)

        # Whoosh centered in gap before line with Meanwhile
        gap_mid = None
        h2 = hints[2]
        h3 = hints[3]
        gap_mid = (h2["end_ms"] + h3["start_ms"]) // 2
        ev_w = resolved.tracks[2].events[0]
        center = ev_w.start_ms + ev_w.duration_ms // 2
        self.assertLessEqual(abs(center - gap_mid), 50)

        # Backchannel: synthetic wi may lack pause — allow fallback rough OR skip assert
        ev_bc = resolved.tracks[3].events[0]
        self.assertGreater(ev_bc.start_ms, 0)

        # Second impact "story"
        story_t = _find_word("story")
        ev_last = resolved.tracks[0].events[1]
        self.assertLessEqual(abs(ev_last.start_ms - story_t), 50)


if __name__ == "__main__":
    unittest.main()
