"""
Music generation endpoints backed by ACE-Step.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse

from ..config import config
from ..models.schemas import (
    ErrorResponse,
    MusicGenerateRequest,
    MusicGenerateResponse,
    MusicHealthResponse,
    MusicHistoryListResponse,
    MusicHistoryItemResponse,
    MusicLyricsRequest,
    MusicLyricsResponse,
    MusicPresetListResponse,
    MusicPresetRequest,
    MusicPresetResponse,
    MusicSimpleGenerateRequest,
    MusicStatusResponse,
)
from ..models.music_storage import music_storage
from ..services.music_generator import music_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/music", tags=["music"])


@router.post(
    "/generate",
    response_model=MusicGenerateResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generate_music(
    request: MusicGenerateRequest,
    http_request: Request,
) -> MusicGenerateResponse:
    """Submit an ACE-Step custom generation task and return a task ID."""
    client_ip = http_request.client.host if http_request.client else "unknown"
    logger.info("Music generation request from %s", client_ip)

    try:
        payload = {
            "prompt": request.caption,
            "lyrics": request.lyrics,
            "bpm": request.bpm,
            "keyscale": request.keyscale,
            "timesignature": request.timesignature,
            "duration": request.duration,
            "vocal_language": request.vocal_language,
            "instrumental": request.instrumental,
            "thinking": request.thinking,
            "inference_steps": request.inference_steps,
            "batch_size": request.batch_size,
            "seed": request.seed,
            "audio_format": request.audio_format,
        }
        clean_payload = {k: v for k, v in payload.items() if v is not None}
        task_id = await music_generator.generate_music(clean_payload)
        music_storage.create_history_entry(
            task_id=task_id,
            mode="custom",
            request_payload=clean_payload,
        )
        return MusicGenerateResponse(
            success=True,
            message="Music generation task submitted",
            task_id=task_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Music generation submission failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Music generation request failed: {exc}",
        ) from exc


@router.get(
    "/status/{task_id}",
    response_model=MusicStatusResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_music_status(task_id: str) -> MusicStatusResponse:
    """Get status and generated file URLs for an ACE-Step task."""
    try:
        result = await music_generator.get_status(task_id)
        music_storage.update_history_by_task(
            task_id,
            status=result.get("status"),
            audios=result.get("audios"),
            metadata=result.get("metadata"),
            error=result.get("error"),
        )
        return MusicStatusResponse(
            success=True,
            message="Task status retrieved",
            task_id=task_id,
            status=result.get("status", "running"),
            audios=result.get("audios", []),
            metadata=result.get("metadata", []),
            error=result.get("error"),
        )
    except Exception as exc:
        logger.exception("Music status query failed for task %s: %s", task_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task status query failed: {exc}",
        ) from exc


@router.post(
    "/generate-lyrics",
    response_model=MusicLyricsResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generate_lyrics(request: MusicLyricsRequest) -> MusicLyricsResponse:
    """Generate song lyrics with Ollama assistance."""
    try:
        result = await music_generator.generate_lyrics(
            description=request.description,
            genre=request.genre,
            mood=request.mood,
            language=request.language,
            duration_hint=request.duration_hint,
        )
        return MusicLyricsResponse(
            success=True,
            message="Lyrics generated successfully",
            lyrics=result.get("lyrics", ""),
            caption=result.get("caption", ""),
        )
    except Exception as exc:
        logger.exception("Lyrics generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lyrics generation failed: {exc}",
        ) from exc


@router.post(
    "/simple-generate",
    response_model=MusicGenerateResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def simple_generate_music(request: MusicSimpleGenerateRequest) -> MusicGenerateResponse:
    """Submit a description-driven music generation task."""
    try:
        effective_language = request.vocal_language
        if not request.instrumental and not effective_language:
            effective_language = "en"
        task_id = await music_generator.create_sample(
            query=request.description,
            instrumental=request.instrumental,
            vocal_language=effective_language,
            duration=request.duration,
            batch_size=request.batch_size,
        )
        music_storage.create_history_entry(
            task_id=task_id,
            mode="simple",
            request_payload={
                "description": request.description,
                "instrumental": request.instrumental,
                "vocal_language": request.vocal_language,
                "duration": request.duration,
                "batch_size": request.batch_size,
            },
        )
        return MusicGenerateResponse(
            success=True,
            message="Simple music generation task submitted",
            task_id=task_id,
        )
    except Exception as exc:
        logger.exception("Simple music generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simple music generation failed: {exc}",
        ) from exc


@router.get(
    "/download/{filename}",
    responses={
        404: {"model": ErrorResponse},
    },
)
async def download_music(filename: str) -> FileResponse:
    """Download locally stored generated music."""
    file_path = config.MUSIC_OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Music file not found: {filename}",
        )

    media_type = "audio/mpeg"
    suffix = Path(filename).suffix.lower()
    if suffix == ".wav":
        media_type = "audio/wav"
    elif suffix == ".flac":
        media_type = "audio/flac"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )


@router.get("/health", response_model=MusicHealthResponse)
async def music_health() -> MusicHealthResponse:
    """Return ACE-Step availability and runtime status."""
    return MusicHealthResponse(**music_generator.health())


@router.get("/presets", response_model=MusicPresetListResponse)
async def list_music_presets() -> MusicPresetListResponse:
    """List saved music presets."""
    presets = music_storage.list_presets()
    return MusicPresetListResponse(presets=presets, total=len(presets))


@router.post(
    "/presets",
    response_model=MusicPresetResponse,
    responses={400: {"model": ErrorResponse}},
)
async def create_music_preset(request: MusicPresetRequest) -> MusicPresetResponse:
    """Create a saved music preset."""
    item = music_storage.create_preset(
        name=request.name.strip(),
        mode=request.mode,
        values=request.values or {},
    )
    return MusicPresetResponse(**item)


@router.put(
    "/presets/{preset_id}",
    response_model=MusicPresetResponse,
    responses={404: {"model": ErrorResponse}},
)
async def update_music_preset(preset_id: str, request: MusicPresetRequest) -> MusicPresetResponse:
    """Update an existing music preset."""
    item = music_storage.update_preset(
        preset_id=preset_id,
        name=request.name.strip(),
        mode=request.mode,
        values=request.values or {},
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")
    return MusicPresetResponse(**item)


@router.delete(
    "/presets/{preset_id}",
    responses={404: {"model": ErrorResponse}},
)
async def delete_music_preset(preset_id: str) -> dict:
    """Delete a music preset."""
    ok = music_storage.delete_preset(preset_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")
    return {"success": True, "message": "Preset deleted"}


@router.get("/history", response_model=MusicHistoryListResponse)
async def list_music_history(limit: int = 50) -> MusicHistoryListResponse:
    """List music generation history."""
    items = music_storage.list_history(limit=limit)
    return MusicHistoryListResponse(history=items, total=len(items))


@router.get(
    "/history/{history_id}",
    response_model=MusicHistoryItemResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_music_history_item(history_id: str) -> MusicHistoryItemResponse:
    """Get one music history item."""
    items = music_storage.list_history(limit=5000)
    match = next((item for item in items if item.get("id") == history_id), None)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History item not found")
    return MusicHistoryItemResponse(**match)


@router.delete(
    "/history/{history_id}",
    responses={404: {"model": ErrorResponse}},
)
async def delete_music_history_item(history_id: str) -> dict:
    """Delete a music history item."""
    ok = music_storage.delete_history(history_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History item not found")
    return {"success": True, "message": "History item deleted"}
