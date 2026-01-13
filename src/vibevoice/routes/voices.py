"""
Voice management endpoints.
"""
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from ..models.schemas import (
    AudioValidationFeedback,
    ErrorResponse,
    IndividualFileAnalysis,
    VoiceCreateResponse,
    VoiceListResponse,
    VoiceResponse,
)
from ..services.voice_manager import voice_manager

router = APIRouter(prefix="/api/v1/voices", tags=["voices"])


@router.post(
    "",
    response_model=VoiceCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_voice(
    name: str,
    description: str = None,
    audio_files: list[UploadFile] = File(...),
) -> VoiceCreateResponse:
    """
    Create a custom voice from uploaded audio files.

    Args:
        name: Voice name (must be unique)
        description: Optional voice description
        audio_files: List of audio files to combine for training

    Returns:
        Voice creation response with voice details
    """
    if not audio_files or len(audio_files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one audio file is required",
        )

    # Save uploaded files temporarily
    temp_files = []
    try:
        for audio_file in audio_files:
            # Validate file type
            if not audio_file.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All files must have a filename",
                )

            # Create temporary file
            import tempfile

            suffix = Path(audio_file.filename).suffix
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_files.append(Path(temp_file.name))

            # Write uploaded content
            content = await audio_file.read()
            temp_file.write(content)
            temp_file.close()

        # Create voice
        try:
            voice_data = voice_manager.create_custom_voice(
                name=name,
                description=description,
                audio_files=temp_files,
            )

            # Parse created_at if it's a string
            created_at = voice_data.get("created_at")
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    created_at = None

            voice_response = VoiceResponse(
                id=voice_data["id"],
                name=voice_data["name"],
                description=voice_data.get("description"),
                type=voice_data.get("type", "custom"),
                created_at=created_at,
                audio_files=voice_data.get("audio_files"),
            )

            # Parse validation feedback if present
            validation_feedback = None
            if "validation_feedback" in voice_data:
                feedback_data = voice_data["validation_feedback"]
                individual_files = [
                    IndividualFileAnalysis(**file_data) for file_data in feedback_data.get("individual_files", [])
                ]
                validation_feedback = AudioValidationFeedback(
                    total_duration_seconds=feedback_data.get("total_duration_seconds", 0.0),
                    individual_files=individual_files,
                    warnings=feedback_data.get("warnings", []),
                    recommendations=feedback_data.get("recommendations", []),
                    quality_metrics=feedback_data.get("quality_metrics", {}),
                )

            # Build message with warnings if any
            message = f"Voice '{name}' created successfully"
            if validation_feedback and validation_feedback.warnings:
                warning_count = len(validation_feedback.warnings)
                message += f" ({warning_count} warning{'s' if warning_count > 1 else ''} about audio quality/duration)"

            return VoiceCreateResponse(
                success=True,
                message=message,
                voice=voice_response,
                validation_feedback=validation_feedback,
            )

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()


@router.get(
    "",
    response_model=VoiceListResponse,
    responses={
        500: {"model": ErrorResponse},
    },
)
async def list_voices() -> VoiceListResponse:
    """
    List all available voices (default + custom).

    Returns:
        List of all voices with metadata
    """
    try:
        voices_data = voice_manager.list_all_voices()

        voices = []
        for voice_data in voices_data:
            # Parse created_at if it's a string
            created_at = voice_data.get("created_at")
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    created_at = None

            voices.append(
                VoiceResponse(
                    id=voice_data["id"],
                    name=voice_data["name"],
                    description=voice_data.get("description"),
                    type=voice_data.get("type", "default"),
                    created_at=created_at,
                    audio_files=voice_data.get("audio_files"),
                )
            )

        return VoiceListResponse(voices=voices, total=len(voices))

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list voices: {str(e)}",
        ) from e


@router.delete(
    "/{voice_id}",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def delete_voice(voice_id: str) -> JSONResponse:
    """
    Delete a custom voice.

    Args:
        voice_id: Voice identifier

    Returns:
        Success response
    """
    try:
        # Check if voice exists
        voice_data = voice_manager.get_voice(voice_id)
        if not voice_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Voice '{voice_id}' not found",
            )

        # Delete voice
        deleted = voice_manager.delete_custom_voice(voice_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Voice '{voice_id}' not found",
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": f"Voice '{voice_id}' deleted successfully",
            },
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete voice: {str(e)}",
        ) from e
