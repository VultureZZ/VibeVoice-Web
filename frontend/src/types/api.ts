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
  speaker_instructions?: string[];
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

export type RecordingType = 'meeting' | 'call' | 'memo' | 'interview' | 'other';

export interface TranscriptSpeakerSegment {
  speaker_id: string;
  start_ms: number;
  end_ms: number;
  text: string;
  confidence: number;
}

export interface TranscriptSpeaker {
  id: string;
  label?: string | null;
  voice_library_match?: string | null;
  match_confidence?: number | null;
  talk_time_seconds: number;
  segment_count: number;
  summary?: string | null;
  audio_segment_path?: string | null;
}

export interface TranscriptActionItem {
  action: string;
  owner?: string | null;
  due_hint?: string | null;
  priority: 'low' | 'medium' | 'high' | string;
}

export interface TranscriptAnalysis {
  summary: string;
  action_items: TranscriptActionItem[];
  key_decisions: string[];
  open_questions: string[];
  topics_discussed: string[];
  sentiment: string;
  duration_formatted: string;
}

export interface TranscriptItem {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  duration_seconds?: number;
  file_name: string;
  file_size_bytes: number;
  language: string;
  recording_type: RecordingType;
  speakers: TranscriptSpeaker[];
  transcript: TranscriptSpeakerSegment[];
  analysis?: TranscriptAnalysis | null;
  error?: string | null;
  progress_pct: number;
  current_stage?: string | null;
}

export interface TranscriptUploadResponse {
  transcript_id: string;
  status: string;
  message: string;
  estimated_wait_seconds: number;
}

export interface TranscriptStatusResponse {
  transcript_id: string;
  status: string;
  progress_pct: number;
  current_stage?: string | null;
  duration_seconds?: number | null;
  speakers_detected?: number | null;
  error?: string | null;
}

export interface TranscriptListResponse {
  transcripts: TranscriptItem[];
  total: number;
  limit: number;
  offset: number;
}