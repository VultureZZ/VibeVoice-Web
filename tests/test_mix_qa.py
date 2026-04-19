"""Unit tests for mix_qa metrics."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from app.services.mix_qa import run_mix_qa


class TestMixQA(unittest.TestCase):
    def test_run_mix_qa_returns_all_checks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.wav"
            y = np.sin(np.linspace(0, 500, 24000)).astype(np.float32) * 0.1
            sf.write(str(p), y, 48000)
            qa = run_mix_qa(
                p,
                target_lufs=-20.0,
                plan_duration_seconds=0.5,
                dialogue_regions_ms=[(0, 500)],
                plan=None,
            )
            names = {c["name"] for c in qa["checks"]}
            self.assertIn("loudness_lufs", names)
            self.assertIn("clip_count", names)
            self.assertIn("summary", qa)


if __name__ == "__main__":
    unittest.main()
