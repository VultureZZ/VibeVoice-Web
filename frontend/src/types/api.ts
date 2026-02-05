/**
 * TypeScript interfaces matching API schemas
 */

export interface SpeechSettings {
  language: string;
  output_format: string;
  sample_rate: number;
}

export interface SpeechGenerateRequest {
  transcript: string;
  speakers: string[];
  settings?: SpeechSettings;
}

export interface SpeechGenerateResponse {
  success: boolean;
  message: string;
  audio_url?: string;
  file_path?: string;
}

export interface VoiceQualityAnalysis {
  clone_quality: string;
  issues: string[];
  recording_quality_score: number;
  background_music_detected: boolean;
  background_noise_detected: boolean;
}

export interface VoiceResponse {
  id: string;
  name: string;
  display_name?: string;
  language_code?: string;
  language_label?: string;
  gender?: 'male' | 'female' | 'neutral' | 'unknown' | string;
  description?: string;
  type: string;
  created_at?: string;
  audio_files?: string[];
  image_url?: string;
  quality_analysis?: VoiceQualityAnalysis;
}

export interface VoiceListResponse {
  voices: VoiceResponse[];
  total: number;
}

export interface IndividualFileAnalysis {
  filename: string;
  duration_seconds?: number;
  sample_rate?: number;
  channels?: number;
  file_size_bytes?: number;
  file_size_mb?: number;
  warnings: string[];
  error?: string;
}

export interface AudioValidationFeedback {
  total_duration_seconds: number;
  individual_files: IndividualFileAnalysis[];
  warnings: string[];
  recommendations: string[];
  quality_metrics: Record<string, unknown>;
}

export interface VoiceCreateResponse {
  success: boolean;
  message: string;
  voice?: VoiceResponse;
  validation_feedback?: AudioValidationFeedback;
}

export interface AudioClipRange {
  start_seconds: number;
  end_seconds: number;
}

export interface ErrorResponse {
  error: string;
  detail?: string;
}

export interface HealthCheckResponse {
  status: string;
  service: string;
  version: string;
}

export interface PodcastScriptRequest {
  url: string;
  voices: string[];
  genre: string;
  duration: string;
  ollama_url?: string;
  ollama_model?: string;
}

export interface PodcastScriptResponse {
  success: boolean;
  message: string;
  script?: string;
  warnings?: string[];
}

export interface PodcastGenerateRequest {
  script: string;
  voices: string[];
  settings?: SpeechSettings;
  title?: string;
  source_url?: string;
  genre?: string;
  duration?: string;
  save_to_library?: boolean;
}

export interface PodcastGenerateResponse {
  success: boolean;
  message: string;
  audio_url?: string;
  file_path?: string;
  script?: string;
  podcast_id?: string;
  warnings?: string[];
}

export interface PodcastItem {
  id: string;
  title: string;
  voices: string[];
  source_url?: string;
  genre?: string;
  duration?: string;
  created_at?: string;
  audio_url?: string;
}

export interface PodcastListResponse {
  podcasts: PodcastItem[];
  total: number;
}

export interface VoiceProfile {
  cadence?: string;
  tone?: string;
  vocabulary_style?: string;
  sentence_structure?: string;
  unique_phrases: string[];
  keywords: string[];
  profile_text?: string;
  created_at?: string;
  updated_at?: string;
}

export interface VoiceProfileApplyRequest {
  cadence?: string;
  tone?: string;
  vocabulary_style?: string;
  sentence_structure?: string;
  unique_phrases?: string[];
  keywords?: string[];
  profile_text?: string;
}

export interface VoiceProfileRequest {
  keywords?: string[];
  ollama_url?: string;
  ollama_model?: string;
}

export interface VoiceProfileResponse {
  success: boolean;
  message: string;
  profile?: VoiceProfile;
}

export interface VoiceProfileFromAudioResponse {
  success: boolean;
  message: string;
  profile?: VoiceProfile;
  transcript?: string;
  validation_feedback?: AudioValidationFeedback;
}

export interface VoiceUpdateRequest {
  name?: string;
  description?: string;
  language_code?: string;
  gender?: string;
}

export interface VoiceUpdateResponse {
  success: boolean;
  message: string;
  voice?: VoiceResponse;
}