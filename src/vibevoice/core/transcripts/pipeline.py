"""
Transcript processing pipeline orchestration.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from ...config import config
from ...models.transcript_storage import transcript_storage
from .audio_extractor import transcript_audio_extractor
from .analyzer import transcript_analyzer
from .diarizer import transcript_diarizer
from .reporter import transcript_reporter
from .speaker_matcher import transcript_speaker_matcher
from .transcriber import transcript_transcriber

logger = logging.getLogger(__name__)


def _extract_unique_speakers(segments: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for seg in segments:
        sid = seg.get("speaker_id")
        if isinstance(sid, str) and sid not in seen:
            seen.add(sid)
            ordered.append(sid)
    return ordered


def _build_speakers(
    speaker_ids: list[str],
    segments: list[dict[str, Any]],
    matches: list[dict[str, Any]],
    audio_paths: dict[str, str],
) -> list[dict[str, Any]]:
    match_map = {m["speaker_id"]: m for m in matches}
    out: list[dict[str, Any]] = []
    for sid in speaker_ids:
        speaker_segments = [x for x in segments if x.get("speaker_id") == sid]
        talk_time_seconds = sum(
            max(0.0, (float(x.get("end_ms", 0)) - float(x.get("start_ms", 0))) / 1000.0) for x in speaker_segments
        )
        m = match_map.get(sid) or {}
        out.append(
            {
                "id": sid,
                "label": None,
                "voice_library_match": m.get("voice_id"),
                "match_confidence": m.get("confidence"),
                "talk_time_seconds": talk_time_seconds,
                "segment_count": len(speaker_segments),
                "summary": None,
                "audio_segment_path": audio_paths.get(sid),
            }
        )
    return out


class TranscriptPipeline:
    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(max(1, config.TRANSCRIPT_MAX_CONCURRENT_JOBS))

    async def _set_status(
        self,
        transcript_id: str,
        *,
        status: str,
        progress: int,
        stage: str,
        error: str | None = None,
    ) -> None:
        transcript_storage.set_status(
            transcript_id,
            status=status,
            progress_pct=progress,
            current_stage=stage,
            error=error,
        )

    async def process_transcript(self, transcript_id: str, wav_path: str) -> None:
        async with self._semaphore:
            transcript = transcript_storage.get_transcript(transcript_id)
            if not transcript:
                raise ValueError(f"Transcript not found: {transcript_id}")

            try:
                await self._set_status(
                    transcript_id, status="transcribing", progress=10, stage="Transcribing audio..."
                )
                raw_transcript = await transcript_transcriber.transcribe(
                    wav_path, language=transcript.get("language") or "en"
                )
                aligned = await transcript_transcriber.align(raw_transcript, wav_path)

                await self._set_status(
                    transcript_id, status="diarizing", progress=40, stage="Identifying speakers..."
                )
                diarization = await transcript_diarizer.run(wav_path)
                segments = await transcript_diarizer.assign_speakers(aligned, diarization)

                await self._set_status(
                    transcript_id, status="matching", progress=60, stage="Matching speakers with voice library..."
                )
                speaker_ids = _extract_unique_speakers(segments)
                matches = await transcript_speaker_matcher.match_all(speaker_ids, wav_path, diarization)

                await self._set_status(
                    transcript_id, status="matching", progress=70, stage="Extracting speaker audio segments..."
                )
                speaker_audio_paths = await transcript_audio_extractor.extract_all(
                    wav_path, speaker_ids, diarization, transcript_id
                )

                speakers = _build_speakers(speaker_ids, segments, matches, speaker_audio_paths)
                transcript_storage.update_transcript(
                    transcript_id,
                    transcript=segments,
                    speakers=speakers,
                    converted_path=wav_path,
                )

                all_matched = all(bool(s.get("voice_library_match")) for s in speakers)
                single_speaker = len(speakers) <= 1

                if all_matched or single_speaker or len(speakers) == 0:
                    await self.run_analysis(transcript_id)
                else:
                    await self._set_status(
                        transcript_id,
                        status="awaiting_labels",
                        progress=75,
                        stage="Please label unrecognized speakers.",
                    )
            except Exception as exc:
                logger.exception("Transcript pipeline failed for %s", transcript_id)
                await self._set_status(
                    transcript_id,
                    status="failed",
                    progress=100,
                    stage="Processing failed.",
                    error=str(exc),
                )
                raise

    async def run_analysis(self, transcript_id: str) -> None:
        transcript = transcript_storage.get_transcript(transcript_id)
        if not transcript:
            raise ValueError(f"Transcript not found: {transcript_id}")

        await self._set_status(
            transcript_id, status="analyzing", progress=80, stage="Generating transcript analysis..."
        )
        analysis = await transcript_analyzer.analyze(
            transcript.get("transcript", []),
            transcript.get("speakers", []),
            transcript.get("recording_type") or "meeting",
            transcript.get("duration_seconds"),
        )

        transcript_storage.update_transcript(transcript_id, analysis=analysis)

        await self._set_status(
            transcript_id, status="analyzing", progress=95, stage="Generating report..."
        )
        await transcript_reporter.generate_pdf(
            transcript_id,
            analysis,
            transcript.get("transcript", []),
            transcript.get("speakers", []),
            title=transcript.get("title") or "Transcript",
            recording_type=transcript.get("recording_type") or "meeting",
        )

        await self._set_status(
            transcript_id, status="complete", progress=100, stage="Processing complete."
        )


transcript_pipeline = TranscriptPipeline()

