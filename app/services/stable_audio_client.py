"""
Stable Audio Open client (skeleton).

Set STABLE_AUDIO_OPEN_ENABLED and implement ``generate`` when the backend is wired.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class StableAudioOpenClient:
    """Placeholder for Stable Audio Open–compatible SFX generation."""

    async def generate(
        self,
        *,
        prompt: str,
        duration_seconds: float,
        out_path: Path,
    ) -> Optional[Path]:
        """
        Generate a short SFX clip to ``out_path``.

        Returns the output path on success, or ``None`` if generation is not available.
        """
        logger.warning("StableAudioOpenClient.generate is not implemented; skipping SFX generation")
        return None


stable_audio_open_client = StableAudioOpenClient()
