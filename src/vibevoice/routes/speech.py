"""
Speech generation endpoints.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from ..models.schemas import ErrorResponse, SpeechGenerateRequest, SpeechGenerateResponse
from ..services.voice_generator import voice_generator

router = APIRouter(prefix="/api/v1/speech", tags=["speech"])


@router.post(
    "/generate",
    response_model=SpeechGenerateResponse,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generate_speech(request: SpeechGenerateRequest) -> SpeechGenerateResponse:
    """
    Generate speech from text transcript.

    Args:
        request: Speech generation request with transcript, speakers, and settings

    Returns:
        Speech generation response with audio file path
    """
    try:
        # Format transcript if needed
        formatted_transcript = voice_generator.format_transcript(
            request.transcript, request.speakers
        )

        # Generate speech
        output_path = voice_generator.generate_speech(
            transcript=formatted_transcript,
            speakers=request.speakers,
        )

        # Return response with file path
        return SpeechGenerateResponse(
            success=True,
            message="Speech generated successfully",
            audio_url=f"/api/v1/speech/download/{output_path.name}",
            file_path=str(output_path),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech generation failed: {str(e)}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.get(
    "/download/{filename}",
    responses={
        404: {"model": ErrorResponse},
    },
)
async def download_speech(filename: str) -> FileResponse:
    """
    Download generated speech file.

    Args:
        filename: Name of the generated audio file

    Returns:
        Audio file as binary response
    """
    from ..config import config

    file_path = config.OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found: {filename}",
        )

    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        filename=filename,
    )
