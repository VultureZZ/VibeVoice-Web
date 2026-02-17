"""
Transcript CRUD/upload/job management service.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from pydub import AudioSegment

from ..config import config
from ..core.transcripts.pipeline import transcript_pipeline
from ..models.transcript_storage import transcript_storage

logger = logging.getLogger(__name__)


class TranscriptService:
    def __init__(self) -> None:
        self._jobs: dict[str, asyncio.Task[None]] = {}

    @staticmethod
    def _ext_from_filename(filename: str) -> str:
        return (Path(filename).suffix or "").lower().lstrip(".")

    def _validate_upload(self, filename: str, size_bytes: int) -> None:
        ext = self._ext_from_filename(filename)
        if ext not in config.TRANSCRIPT_SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format '{ext}'. Supported: {', '.join(config.TRANSCRIPT_SUPPORTED_FORMATS)}"
            )

        max_size = config.TRANSCRIPT_MAX_UPLOAD_MB * 1024 * 1024
        if size_bytes > max_size:
            raise ValueError(
                f"File too large ({size_bytes} bytes). Max is {config.TRANSCRIPT_MAX_UPLOAD_MB}MB."
            )

    async def _save_upload(self, upload: UploadFile, transcript_id: str) -> tuple[str, int]:
        uploads_dir = config.TRANSCRIPTS_DIR / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(upload.filename or "audio.wav").suffix.lower() or ".wav"
        file_path = uploads_dir / f"{transcript_id}{ext}"
        content = await upload.read()
        if not content:
            raise ValueError("Uploaded file is empty.")
        self._validate_upload(upload.filename or file_path.name, len(content))
        file_path.write_bytes(content)
        return str(file_path), len(content)

    async def _convert_to_wav(self, source_path: str, transcript_id: str) -> str:
        transcripts_json_dir = config.TRANSCRIPTS_DIR / "json"
        transcripts_json_dir.mkdir(parents=True, exist_ok=True)
        output_path = transcripts_json_dir / f"{transcript_id}.wav"

        segment = AudioSegment.from_file(source_path)
        segment = segment.set_frame_rate(16000).set_channels(1)
        segment.export(str(output_path), format="wav")
        return str(output_path)

    async def _run_job(self, transcript_id: str, source_path: str) -> None:
        try:
            transcript_storage.set_status(
                transcript_id,
                status="transcribing",
                progress_pct=5,
                current_stage="Converting audio format...",
            )
            wav_path = await self._convert_to_wav(source_path, transcript_id)
            segment = AudioSegment.from_wav(wav_path)
            duration_seconds = len(segment) / 1000.0
            transcript_storage.update_transcript(
                transcript_id,
                duration_seconds=duration_seconds,
                converted_path=wav_path,
            )
            await transcript_pipeline.process_transcript(transcript_id, wav_path)
        finally:
            self._jobs.pop(transcript_id, None)

    async def upload_and_queue(
        self,
        audio_file: UploadFile,
        *,
        title: Optional[str] = None,
        language: str = "en",
        recording_type: str = "meeting",
    ) -> dict:
        transcript_id = str(uuid.uuid4())
        upload_path, size_bytes = await self._save_upload(audio_file, transcript_id)
        final_title = title or Path(audio_file.filename or "Untitled recording").stem
        transcript_storage.create_transcript(
            transcript_id,
            title=final_title,
            file_name=audio_file.filename or Path(upload_path).name,
            file_size_bytes=size_bytes,
            language=language or "en",
            recording_type=recording_type or "meeting",
            upload_path=upload_path,
        )
        transcript_storage.set_status(
            transcript_id,
            status="queued",
            progress_pct=0,
            current_stage="Queued for processing",
        )
        task = asyncio.create_task(self._run_job(transcript_id, upload_path))
        self._jobs[transcript_id] = task
        return {
            "transcript_id": transcript_id,
            "status": "queued",
            "message": "File uploaded successfully. Processing queued.",
            "estimated_wait_seconds": 30,
        }

    def get(self, transcript_id: str) -> Optional[dict]:
        return transcript_storage.get_transcript(transcript_id)

    def list(self, limit: int = 20, offset: int = 0, status: Optional[str] = None, recording_type: Optional[str] = None):
        return transcript_storage.list_transcripts(
            limit=limit,
            offset=offset,
            status=status,
            recording_type=recording_type,
        )

    def delete(self, transcript_id: str) -> bool:
        data = transcript_storage.get_transcript(transcript_id)
        if not data:
            return False

        for path_key in ("upload_path", "converted_path"):
            path_val = data.get(path_key)
            if path_val:
                path = Path(path_val)
                if path.exists():
                    path.unlink(missing_ok=True)

        meeting_dir = config.TRANSCRIPTS_DIR / "segments" / transcript_id
        if meeting_dir.exists():
            for p in meeting_dir.glob("*"):
                if p.is_file():
                    p.unlink(missing_ok=True)
            meeting_dir.rmdir()

        reports_dir = config.TRANSCRIPTS_DIR / "reports"
        for ext in ("pdf", "json", "md"):
            candidate = reports_dir / f"{transcript_id}.{ext}"
            if candidate.exists():
                candidate.unlink(missing_ok=True)

        return transcript_storage.delete_transcript(transcript_id)

    def cleanup_old(self) -> int:
        items, _ = transcript_storage.list_transcripts(limit=100000, offset=0)
        removed = 0
        now = datetime.utcnow()
        retention_seconds = config.TRANSCRIPT_RETENTION_HOURS * 3600
        for item in items:
            created_at = item.get("created_at")
            if not created_at:
                continue
            try:
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                continue
            age_seconds = (now - created_dt).total_seconds()
            if age_seconds > retention_seconds and self.delete(item.get("id", "")):
                removed += 1
        return removed


transcript_service = TranscriptService()

