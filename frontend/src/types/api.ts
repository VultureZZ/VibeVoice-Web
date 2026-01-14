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

export interface VoiceResponse {
  id: string;
  name: string;
  description?: string;
  type: string;
  created_at?: string;
  audio_files?: string[];
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
}

export interface PodcastGenerateRequest {
  script: string;
  voices: string[];
  settings?: SpeechSettings;
}

export interface PodcastGenerateResponse {
  success: boolean;
  message: string;
  audio_url?: string;
  file_path?: string;
  script?: string;
}