#!/usr/bin/env python3
"""Unit tests for voice_prosody helpers."""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
for p in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from app.services.voice_prosody import (
    emotion_line_energy_db,
    fallback_voice_direction_for_script,
    synthetic_timing_hints_from_segments,
)


class TestSyntheticHints(unittest.TestCase):
    def test_builds_per_dialogue_line(self):
        segs = [
            {"segment_type": "dialogue", "text": "a", "speaker": "Speaker 1", "duration_hint": 1.0},
            {"segment_type": "dialogue", "text": "b", "speaker": "Speaker 2", "duration_hint": 2.0},
        ]
        h = synthetic_timing_hints_from_segments(segs)
        self.assertEqual(len(h), 2)
        self.assertEqual(h[0]["line_index"], 0)
        self.assertLess(h[0]["start_ms"], h[1]["start_ms"])


class TestFallbackVD(unittest.TestCase):
    def test_one_line_per_speaker_line(self):
        script = "Speaker 1: Hello world.\nSpeaker 2: Hi there."
        rows = fallback_voice_direction_for_script(script, "News")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["emotion"], "neutral")


class TestEnergyDb(unittest.TestCase):
    def test_excited_louder_than_somber(self):
        self.assertGreater(emotion_line_energy_db("excited"), emotion_line_energy_db("somber"))


if __name__ == "__main__":
    unittest.main()
