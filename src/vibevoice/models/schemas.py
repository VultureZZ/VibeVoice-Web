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


class PodcastScriptRequest(BaseModel):
    """Request model for generating podcast script from URL."""

    url: str = Field(..., description="URL of the article to convert to podcast")
    voices: List[str] = Field(..., min_length=1, max_length=4, description="List of voice names (1-4 voices)")
    genre: str = Field(..., description="Podcast genre (Comedy, Serious, News, Educational, Storytelling, Interview, Documentary)")
    duration: str = Field(..., description="Target duration (5 min, 10 min, 15 min, 30 min)")
    ollama_url: Optional[str] = Field(None, description="Optional custom Ollama server URL")
    ollama_model: Optional[str] = Field(None, description="Optional custom Ollama model name")


class PodcastScriptResponse(BaseModel):
    """Response model for podcast script generation."""

    success: bool = Field(..., description="Whether script generation was successful")
    message: str = Field(..., description="Status message")
    script: Optional[str] = Field(None, description="Generated podcast script with speaker labels")


class PodcastGenerateRequest(BaseModel):
    """Request model for generating podcast audio from script."""

    script: str = Field(..., description="Podcast script with speaker labels")
    voices: List[str] = Field(..., min_length=1, max_length=4, description="List of voice names (1-4 voices)")
    settings: Optional[SpeechSettings] = Field(default_factory=SpeechSettings, description="Speech generation settings")
    title: Optional[str] = Field(None, description="Optional title for saving into the podcast library")
    source_url: Optional[str] = Field(None, description="Optional source URL (e.g., article URL)")
    genre: Optional[str] = Field(None, description="Optional genre metadata")
    duration: Optional[str] = Field(None, description="Optional duration metadata (e.g., '10 min')")
    save_to_library: bool = Field(default=True, description="Whether to save the generated podcast to the library")


class PodcastGenerateResponse(BaseModel):
    """Response model for podcast audio generation."""

    success: bool = Field(..., description="Whether generation was successful")
    message: str = Field(..., description="Status message")
    audio_url: Optional[str] = Field(None, description="URL to generated audio file")
    file_path: Optional[str] = Field(None, description="Path to generated audio file")
    script: Optional[str] = Field(None, description="Script used for generation")
    podcast_id: Optional[str] = Field(None, description="Podcast library identifier (if saved)")


class PodcastItem(BaseModel):
    """Podcast library item metadata."""

    id: str = Field(..., description="Podcast identifier")
    title: str = Field(..., description="Podcast title")
    voices: List[str] = Field(default_factory=list, description="Voices used in this podcast")
    source_url: Optional[str] = Field(None, description="Source URL (if any)")
    genre: Optional[str] = Field(None, description="Genre metadata (if any)")
    duration: Optional[str] = Field(None, description="Target duration metadata (if any)")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    audio_url: Optional[str] = Field(None, description="Download URL for the podcast audio")


class PodcastListResponse(BaseModel):
    """Podcast library list response."""

    podcasts: List[PodcastItem] = Field(default_factory=list, description="Podcast library items")
    total: int = Field(..., description="Total number of items")


class VoiceProfile(BaseModel):
    """Structured voice profile with speech pattern characteristics."""

    cadence: Optional[str] = Field(None, description="Description of speech rhythm/pace")
    tone: Optional[str] = Field(None, description="Emotional tone and delivery style")
    vocabulary_style: Optional[str] = Field(None, description="Word choice patterns (formal, casual, technical, etc.)")
    sentence_structure: Optional[str] = Field(None, description="Typical sentence patterns (short, long, complex)")
    unique_phrases: List[str] = Field(default_factory=list, description="Common phrases or expressions")
    keywords: List[str] = Field(default_factory=list, description="Keywords for context (e.g., person names)")
    profile_text: Optional[str] = Field(None, description="Full text description of the voice")
    created_at: Optional[datetime] = Field(None, description="Profile creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Profile last update timestamp")


class VoiceProfileApplyRequest(BaseModel):
    """Request model for applying a full voice profile payload to a voice."""

    cadence: Optional[str] = Field(None, description="Description of speech rhythm/pace")
    tone: Optional[str] = Field(None, description="Emotional tone and delivery style")
    vocabulary_style: Optional[str] = Field(None, description="Word choice patterns (formal, casual, technical, etc.)")
    sentence_structure: Optional[str] = Field(None, description="Typical sentence patterns (short, long, complex)")
    unique_phrases: List[str] = Field(default_factory=list, description="Common phrases or expressions")
    keywords: List[str] = Field(default_factory=list, description="Keywords for context (e.g., person names)")
    profile_text: Optional[str] = Field(None, description="Full text description of the voice")


class VoiceProfileRequest(BaseModel):
    """Request model for creating/updating voice profiles."""

    keywords: Optional[List[str]] = Field(None, description="Keywords to enhance profile (e.g., person names)")
    ollama_url: Optional[str] = Field(None, description="Optional custom Ollama server URL")
    ollama_model: Optional[str] = Field(None, description="Optional custom Ollama model name")


class VoiceProfileResponse(BaseModel):
    """Response model for voice profile data."""

    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Status message")
    profile: Optional[VoiceProfile] = Field(None, description="Voice profile data")


class VoiceProfileFromAudioRequest(BaseModel):
    """Request model (logical) for deriving a profile from audio."""

    keywords: Optional[List[str]] = Field(None, description="Optional keywords/context to help profiling")
    ollama_url: Optional[str] = Field(None, description="Optional custom Ollama server URL")
    ollama_model: Optional[str] = Field(None, description="Optional custom Ollama model name")


class VoiceProfileFromAudioResponse(BaseModel):
    """Response model for audio-derived voice profile."""

    success: bool = Field(..., description="Whether profiling was successful")
    message: str = Field(..., description="Status message")
    profile: Optional[VoiceProfile] = Field(None, description="Derived voice profile")
    transcript: Optional[str] = Field(None, description="Transcript derived from the audio")
    validation_feedback: Optional[AudioValidationFeedback] = Field(
        None, description="Audio validation feedback and recommendations"
    )


class VoiceUpdateRequest(BaseModel):
    """Request model for updating voice details."""

    name: Optional[str] = Field(None, min_length=1, description="New voice name")
    description: Optional[str] = Field(None, description="New voice description")


class VoiceUpdateResponse(BaseModel):
    """Response model for voice update."""

    success: bool = Field(..., description="Whether update was successful")
    message: str = Field(..., description="Status message")
    voice: Optional[VoiceResponse] = Field(None, description="Updated voice details")
