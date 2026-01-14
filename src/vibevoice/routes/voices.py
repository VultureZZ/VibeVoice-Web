"""
Voice management endpoints.
"""
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from ..models.schemas import (
    AudioValidationFeedback,
    ErrorResponse,
    IndividualFileAnalysis,
    VoiceCreateResponse,
    VoiceListResponse,
    VoiceProfileApplyRequest,
    VoiceProfileFromAudioResponse,
    VoiceProfile,
    VoiceProfileRequest,
    VoiceProfileResponse,
    VoiceResponse,
    VoiceUpdateRequest,
    VoiceUpdateResponse,
)
from ..services.voice_manager import voice_manager
from ..services.voice_profile_from_audio import voice_profile_from_audio

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
    name: str = Form(...),
    description: str = Form(None),
    audio_files: list[UploadFile] = File(...),
    keywords: str = Form(None),
) -> VoiceCreateResponse:
    """
    Create a custom voice from uploaded audio files.

    Args:
        name: Voice name (must be unique)
        description: Optional voice description
        audio_files: List of audio files to combine for training
        keywords: Optional comma-separated keywords for voice profiling

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

        # Parse keywords if provided
        keywords_list = None
        if keywords:
            keywords_list = [k.strip() for k in keywords.split(",") if k.strip()]

        # Get Ollama settings from form (optional)
        ollama_url = None  # Could be added as form field if needed
        ollama_model = None  # Could be added as form field if needed

        # Create voice
        try:
            voice_data = voice_manager.create_custom_voice(
                name=name,
                description=description,
                audio_files=temp_files,
                keywords=keywords_list,
                ollama_url=ollama_url,
                ollama_model=ollama_model,
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


@router.post(
    "/profile/analyze-audio",
    response_model=VoiceProfileFromAudioResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def analyze_voice_profile_from_audio(
    audio_file: UploadFile = File(...),
    keywords: str = Form(None),
    ollama_url: str = Form(None),
    ollama_model: str = Form(None),
) -> VoiceProfileFromAudioResponse:
    """
    Analyze an audio file and derive a style-oriented VoiceProfile.

    This does NOT create a new voice; it returns a profile that can be applied to any voice.
    """
    if not audio_file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file must have a filename")

    import tempfile
    from pathlib import Path

    suffix = Path(audio_file.filename).suffix
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_path = Path(temp_file.name)

    try:
        content = await audio_file.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is empty")
        temp_file.write(content)
        temp_file.close()

        keywords_list = None
        if keywords:
            keywords_list = [k.strip() for k in keywords.split(",") if k.strip()]

        profile_dict, validation_dict, transcript = voice_profile_from_audio.analyze(
            audio_path=temp_path,
            keywords=keywords_list,
            ollama_url=ollama_url,
            ollama_model=ollama_model,
        )

        # Parse validation feedback
        individual_files = [
            IndividualFileAnalysis(**file_data) for file_data in validation_dict.get("individual_files", [])
        ]
        validation_feedback = AudioValidationFeedback(
            total_duration_seconds=validation_dict.get("total_duration_seconds", 0.0),
            individual_files=individual_files,
            warnings=validation_dict.get("warnings", []),
            recommendations=validation_dict.get("recommendations", []),
            quality_metrics=validation_dict.get("quality_metrics", {}),
        )

        profile = VoiceProfile(
            cadence=profile_dict.get("cadence"),
            tone=profile_dict.get("tone"),
            vocabulary_style=profile_dict.get("vocabulary_style"),
            sentence_structure=profile_dict.get("sentence_structure"),
            unique_phrases=profile_dict.get("unique_phrases", []),
            keywords=profile_dict.get("keywords", []),
            profile_text=profile_dict.get("profile_text"),
            created_at=None,
            updated_at=None,
        )

        return VoiceProfileFromAudioResponse(
            success=True,
            message="Voice profile generated from audio",
            profile=profile,
            transcript=transcript or None,
            validation_feedback=validation_feedback,
        )
    except HTTPException:
        raise
    except RuntimeError as e:
        # RuntimeError is used for Ollama unavailable / model missing, etc.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze audio: {str(e)}",
        ) from e
    finally:
        if temp_path.exists():
            temp_path.unlink()


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


@router.put(
    "/{voice_id}",
    response_model=VoiceUpdateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def update_voice(
    voice_id: str,
    request: VoiceUpdateRequest,
) -> VoiceUpdateResponse:
    """
    Update voice details (name and/or description).

    Args:
        voice_id: Voice identifier
        request: Update request with name and/or description

    Returns:
        Updated voice response
    """
    try:
        # Check if voice exists
        voice_data = voice_manager.get_voice(voice_id)
        if not voice_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Voice '{voice_id}' not found",
            )

        # Update voice
        updated_voice = voice_manager.update_voice(
            voice_id=voice_id,
            name=request.name,
            description=request.description,
        )

        # Parse created_at if it's a string
        created_at = updated_voice.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created_at = None

        voice_response = VoiceResponse(
            id=updated_voice["id"],
            name=updated_voice["name"],
            description=updated_voice.get("description"),
            type=updated_voice.get("type", "custom"),
            created_at=created_at,
            audio_files=updated_voice.get("audio_files"),
        )

        return VoiceUpdateResponse(
            success=True,
            message=f"Voice '{voice_id}' updated successfully",
            voice=voice_response,
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
            detail=f"Failed to update voice: {str(e)}",
        ) from e


@router.get(
    "/{voice_id}/profile",
    response_model=VoiceProfileResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_voice_profile(voice_id: str) -> VoiceProfileResponse:
    """
    Get voice profile.

    Args:
        voice_id: Voice identifier

    Returns:
        Voice profile response
    """
    try:
        from ..models.voice_storage import voice_storage

        # Check if voice exists
        voice_data = voice_manager.get_voice(voice_id)
        if not voice_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Voice '{voice_id}' not found",
            )

        # Get profile
        profile_data = voice_storage.get_voice_profile(voice_id)

        if not profile_data:
            return VoiceProfileResponse(
                success=True,
                message="No profile found for this voice",
                profile=None,
            )

        # Parse timestamps if present
        created_at = profile_data.get("created_at")
        updated_at = profile_data.get("updated_at")

        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created_at = None

        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                updated_at = None

        profile = VoiceProfile(
            cadence=profile_data.get("cadence"),
            tone=profile_data.get("tone"),
            vocabulary_style=profile_data.get("vocabulary_style"),
            sentence_structure=profile_data.get("sentence_structure"),
            unique_phrases=profile_data.get("unique_phrases", []),
            keywords=profile_data.get("keywords", []),
            profile_text=profile_data.get("profile_text"),
            created_at=created_at,
            updated_at=updated_at,
        )

        return VoiceProfileResponse(
            success=True,
            message="Profile retrieved successfully",
            profile=profile,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get voice profile: {str(e)}",
        ) from e


@router.put(
    "/{voice_id}/profile",
    response_model=VoiceProfileResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def apply_voice_profile(
    voice_id: str,
    request: VoiceProfileApplyRequest,
) -> VoiceProfileResponse:
    """
    Apply a provided VoiceProfile payload to a voice.

    This supports both custom voices and default voices.
    """
    try:
        # Ensure voice exists (default voices are valid here too)
        voice_data = voice_manager.get_voice(voice_id)
        if not voice_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Voice '{voice_id}' not found")

        from ..models.voice_storage import voice_storage

        profile_payload = request.model_dump()
        voice_storage.update_voice_profile(voice_id, profile_payload)

        profile_data = voice_storage.get_voice_profile(voice_id)
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Profile applied but no profile data available",
            )

        created_at = profile_data.get("created_at")
        updated_at = profile_data.get("updated_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created_at = None
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                updated_at = None

        profile = VoiceProfile(
            cadence=profile_data.get("cadence"),
            tone=profile_data.get("tone"),
            vocabulary_style=profile_data.get("vocabulary_style"),
            sentence_structure=profile_data.get("sentence_structure"),
            unique_phrases=profile_data.get("unique_phrases", []),
            keywords=profile_data.get("keywords", []),
            profile_text=profile_data.get("profile_text"),
            created_at=created_at,
            updated_at=updated_at,
        )

        return VoiceProfileResponse(success=True, message="Profile applied successfully", profile=profile)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply profile: {str(e)}",
        ) from e


@router.post(
    "/{voice_id}/profile",
    response_model=VoiceProfileResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_or_update_voice_profile(
    voice_id: str,
    request: VoiceProfileRequest,
) -> VoiceProfileResponse:
    """
    Create or update voice profile with optional keywords.

    Args:
        voice_id: Voice identifier
        request: Profile request with optional keywords

    Returns:
        Voice profile response
    """
    try:
        # Check if voice exists
        voice_data = voice_manager.get_voice(voice_id)
        if not voice_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Voice '{voice_id}' not found",
            )

        # Get existing profile
        from ..models.voice_storage import voice_storage

        existing_profile = voice_storage.get_voice_profile(voice_id)

        # Enhance or create profile
        from ..services.voice_profiler import voice_profiler
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            if existing_profile and request.keywords:
                # Enhance existing profile
                logger.info(f"Enhancing existing profile for voice {voice_id} with keywords: {request.keywords}")
                updated_voice = voice_manager.enhance_voice_profile(
                    voice_id=voice_id,
                    keywords=request.keywords or [],
                )
                message = "Profile enhanced successfully"
            else:
                # Create new profile
                logger.info(f"Creating new profile for voice {voice_id} with keywords: {request.keywords}")
                profile = voice_profiler.profile_voice_from_audio(
                    voice_name=voice_data.get("name", voice_id),
                    voice_description=voice_data.get("description"),
                    keywords=request.keywords,
                    ollama_url=request.ollama_url,
                    ollama_model=request.ollama_model,
                )

                if profile:
                    # Ensure keywords are saved
                    if request.keywords:
                        profile["keywords"] = request.keywords
                    voice_storage.update_voice_profile(voice_id, profile)
                    logger.info(f"Profile created and saved for voice {voice_id}")
                    message = "Profile created successfully"
                else:
                    logger.warning(f"Profile creation returned empty profile for voice {voice_id}")
                    message = "Profile creation attempted but returned empty result"
        except RuntimeError as e:
            # RuntimeError means Ollama is not available or model missing
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            ) from e

        # Get updated profile
        profile_data = voice_storage.get_voice_profile(voice_id)

        if not profile_data:
            return VoiceProfileResponse(
                success=True,
                message="Profile operation completed but no profile data available",
                profile=None,
            )

        # Parse timestamps
        created_at = profile_data.get("created_at")
        updated_at = profile_data.get("updated_at")

        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created_at = None

        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                updated_at = None

        profile = VoiceProfile(
            cadence=profile_data.get("cadence"),
            tone=profile_data.get("tone"),
            vocabulary_style=profile_data.get("vocabulary_style"),
            sentence_structure=profile_data.get("sentence_structure"),
            unique_phrases=profile_data.get("unique_phrases", []),
            keywords=profile_data.get("keywords", []),
            profile_text=profile_data.get("profile_text"),
            created_at=created_at,
            updated_at=updated_at,
        )

        return VoiceProfileResponse(
            success=True,
            message=message,
            profile=profile,
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
            detail=f"Failed to create/update voice profile: {str(e)}",
        ) from e


@router.put(
    "/{voice_id}/profile/keywords",
    response_model=VoiceProfileResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def update_voice_profile_keywords(
    voice_id: str,
    request: VoiceProfileRequest,
) -> VoiceProfileResponse:
    """
    Update voice profile keywords and re-profile.

    Args:
        voice_id: Voice identifier
        request: Profile request with keywords

    Returns:
        Voice profile response
    """
    try:
        if not request.keywords:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Keywords are required",
            )

        # Check if voice exists
        voice_data = voice_manager.get_voice(voice_id)
        if not voice_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Voice '{voice_id}' not found",
            )

        # Enhance profile with keywords
        try:
            updated_voice = voice_manager.enhance_voice_profile(
                voice_id=voice_id,
                keywords=request.keywords,
                ollama_url=request.ollama_url,
                ollama_model=request.ollama_model,
            )
        except RuntimeError as e:
            # RuntimeError means Ollama is not available or model missing
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            ) from e

        # Get updated profile
        from ..models.voice_storage import voice_storage

        profile_data = voice_storage.get_voice_profile(voice_id)

        if not profile_data:
            return VoiceProfileResponse(
                success=True,
                message="Profile updated but no profile data available",
                profile=None,
            )

        # Parse timestamps
        created_at = profile_data.get("created_at")
        updated_at = profile_data.get("updated_at")

        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created_at = None

        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                updated_at = None

        profile = VoiceProfile(
            cadence=profile_data.get("cadence"),
            tone=profile_data.get("tone"),
            vocabulary_style=profile_data.get("vocabulary_style"),
            sentence_structure=profile_data.get("sentence_structure"),
            unique_phrases=profile_data.get("unique_phrases", []),
            keywords=profile_data.get("keywords", []),
            profile_text=profile_data.get("profile_text"),
            created_at=created_at,
            updated_at=updated_at,
        )

        return VoiceProfileResponse(
            success=True,
            message="Profile keywords updated successfully",
            profile=profile,
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
            detail=f"Failed to update profile keywords: {str(e)}",
        ) from e


@router.post(
    "/{voice_id}/profile/generate",
    response_model=VoiceProfileResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generate_voice_profile(
    voice_id: str,
    request: VoiceProfileRequest,
) -> VoiceProfileResponse:
    """
    Manually trigger voice profile generation.

    Args:
        voice_id: Voice identifier
        request: Profile request with optional keywords

    Returns:
        Voice profile response
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Check if voice exists
        voice_data = voice_manager.get_voice(voice_id)
        if not voice_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Voice '{voice_id}' not found",
            )

        # Get existing profile
        from ..models.voice_storage import voice_storage
        from ..services.voice_profiler import voice_profiler

        existing_profile = voice_storage.get_voice_profile(voice_id)

        logger.info(f"Manually generating profile for voice {voice_id} with keywords: {request.keywords}")

        # Generate or enhance profile
        try:
            if existing_profile and request.keywords:
                # Enhance existing profile
                profile = voice_profiler.enhance_profile_with_keywords(
                    voice_name=voice_data.get("name", voice_id),
                    existing_profile=existing_profile,
                    keywords=request.keywords or [],
                    ollama_url=request.ollama_url,
                    ollama_model=request.ollama_model,
                )
                message = "Profile enhanced successfully"
            else:
                # Create new profile
                profile = voice_profiler.profile_voice_from_audio(
                    voice_name=voice_data.get("name", voice_id),
                    voice_description=voice_data.get("description"),
                    keywords=request.keywords,
                    ollama_url=request.ollama_url,
                    ollama_model=request.ollama_model,
                )
                message = "Profile generated successfully"
        except RuntimeError as e:
            # RuntimeError means Ollama is not available or model missing
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            ) from e

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Profile generation returned empty result",
            )

        # Ensure keywords are saved
        if request.keywords:
            profile["keywords"] = request.keywords

        # Save profile
        voice_storage.update_voice_profile(voice_id, profile)
        logger.info(f"Profile saved for voice {voice_id}")

        # Get updated profile
        profile_data = voice_storage.get_voice_profile(voice_id)

        if not profile_data:
            return VoiceProfileResponse(
                success=True,
                message=message,
                profile=None,
            )

        # Parse timestamps
        created_at = profile_data.get("created_at")
        updated_at = profile_data.get("updated_at")

        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created_at = None

        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                updated_at = None

        profile_response = VoiceProfile(
            cadence=profile_data.get("cadence"),
            tone=profile_data.get("tone"),
            vocabulary_style=profile_data.get("vocabulary_style"),
            sentence_structure=profile_data.get("sentence_structure"),
            unique_phrases=profile_data.get("unique_phrases", []),
            keywords=profile_data.get("keywords", []),
            profile_text=profile_data.get("profile_text"),
            created_at=created_at,
            updated_at=updated_at,
        )

        return VoiceProfileResponse(
            success=True,
            message=message,
            profile=profile_response,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to generate profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate profile: {str(e)}",
        ) from e
