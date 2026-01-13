"""
Pydantic models for request/response validation.
"""
from datetime import datetime
from typing import List, Optional

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


class VoiceCreateResponse(BaseModel):
    """Response model for voice creation."""

    success: bool = Field(..., description="Whether creation was successful")
    message: str = Field(..., description="Status message")
    voice: Optional[VoiceResponse] = Field(None, description="Created voice details")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
