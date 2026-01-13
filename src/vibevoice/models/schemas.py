"""
Pydantic models for request/response validation.
"""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SpeechSettings(BaseModel):
    """Settings for speech generation."""

    language: str = Field(default="en", description="Language code (en, zh, etc.)")
    output_format: str = Field(default="wav", description="Output audio format")
    sample_rate: int = Field(default=24000, description="Sample rate in Hz")


class SpeechGenerateRequest(BaseModel):
    """Request model for speech generation."""

    transcript: str = Field(..., description="Transcript text with speaker labels (e.g., 'Speaker 1: Hello')")
    speakers: List[str] = Field(..., min_length=1, description="List of speaker names")
    settings: Optional[SpeechSettings] = Field(default_factory=SpeechSettings, description="Speech generation settings")


class SpeechGenerateResponse(BaseModel):
    """Response model for speech generation."""

    success: bool = Field(..., description="Whether generation was successful")
    message: str = Field(..., description="Status message")
    audio_url: Optional[str] = Field(None, description="URL to generated audio file")
    file_path: Optional[str] = Field(None, description="Path to generated audio file")


class VoiceResponse(BaseModel):
    """Response model for a single voice."""

    id: str = Field(..., description="Voice identifier")
    name: str = Field(..., description="Voice name")
    description: Optional[str] = Field(None, description="Voice description")
    type: str = Field(..., description="Voice type: 'default' or 'custom'")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    audio_files: Optional[List[str]] = Field(None, description="List of audio file names")


class VoiceListResponse(BaseModel):
    """Response model for voice list."""

    voices: List[VoiceResponse] = Field(..., description="List of available voices")
    total: int = Field(..., description="Total number of voices")


class VoiceCreateRequest(BaseModel):
    """Request model for creating a custom voice."""

    name: str = Field(..., min_length=1, description="Voice name (must be unique)")
    description: Optional[str] = Field(None, description="Voice description")


class IndividualFileAnalysis(BaseModel):
    """Analysis result for a single audio file."""

    filename: str = Field(..., description="Name of the audio file")
    duration_seconds: Optional[float] = Field(None, description="Duration in seconds")
    sample_rate: Optional[int] = Field(None, description="Sample rate in Hz")
    channels: Optional[int] = Field(None, description="Number of audio channels")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    file_size_mb: Optional[float] = Field(None, description="File size in megabytes")
    warnings: List[str] = Field(default_factory=list, description="Warnings for this file")
    error: Optional[str] = Field(None, description="Error message if analysis failed")


class AudioValidationFeedback(BaseModel):
    """Feedback from audio file validation."""

    total_duration_seconds: float = Field(..., description="Total duration of all audio files in seconds")
    individual_files: List[IndividualFileAnalysis] = Field(default_factory=list, description="Analysis of each individual file")
    warnings: List[str] = Field(default_factory=list, description="Warnings about audio quality or duration")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for better results")
    quality_metrics: Dict = Field(default_factory=dict, description="Audio quality metrics summary")


class VoiceCreateResponse(BaseModel):
    """Response model for voice creation."""

    success: bool = Field(..., description="Whether creation was successful")
    message: str = Field(..., description="Status message")
    voice: Optional[VoiceResponse] = Field(None, description="Created voice details")
    validation_feedback: Optional[AudioValidationFeedback] = Field(None, description="Audio validation feedback and recommendations")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
