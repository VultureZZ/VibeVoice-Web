/**
 * API client service using Axios
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  SpeechGenerateRequest,
  SpeechGenerateResponse,
  VoiceListResponse,
  VoiceCreateResponse,
  HealthCheckResponse,
  ErrorResponse,
  PodcastScriptRequest,
  PodcastScriptResponse,
  PodcastGenerateRequest,
  PodcastGenerateResponse,
  PodcastListResponse,
  VoiceProfileResponse,
  VoiceProfileRequest,
  VoiceProfileApplyRequest,
  VoiceProfileFromAudioResponse,
  VoiceUpdateRequest,
  VoiceUpdateResponse,
  AudioClipRange,
} from '../types/api';
import { AppSettings } from '../types/settings';

class ApiClient {
  private client: AxiosInstance;
  private baseURL: string;
  private apiKey?: string;

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    this.apiKey = undefined;

    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for API key
    this.client.interceptors.request.use((config) => {
      if (this.apiKey) {
        config.headers['X-API-Key'] = this.apiKey;
      }
      return config;
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ErrorResponse>) => {
        if (error.response) {
          // Server responded with error status
          const errorData = error.response.data;
          const errorMessage = errorData?.detail || errorData?.error || error.message;
          throw new Error(errorMessage);
        } else if (error.request) {
          // Request made but no response received
          throw new Error('Network error: Could not reach the API server');
        } else {
          // Something else happened
          throw new Error(error.message || 'An unexpected error occurred');
        }
      }
    );
  }

  /**
   * Update API configuration
   */
  updateConfig(settings: AppSettings): void {
    this.baseURL = settings.apiEndpoint;
    this.apiKey = settings.apiKey;
    this.client.defaults.baseURL = this.baseURL;
  }

  /**
   * Health check endpoint
   */
  async healthCheck(): Promise<HealthCheckResponse> {
    const response = await this.client.get<HealthCheckResponse>('/health');
    return response.data;
  }

  /**
   * Generate speech from text
   */
  async generateSpeech(request: SpeechGenerateRequest): Promise<SpeechGenerateResponse> {
    const response = await this.client.post<SpeechGenerateResponse>(
      '/api/v1/speech/generate',
      request
    );
    return response.data;
  }

  /**
   * Download generated audio file
   */
  async downloadAudio(filename: string): Promise<Blob> {
    const response = await this.client.get(`/api/v1/speech/download/${filename}`, {
      responseType: 'blob',
    });
    return response.data;
  }

  /**
   * List all available voices
   */
  async listVoices(): Promise<VoiceListResponse> {
    const response = await this.client.get<VoiceListResponse>('/api/v1/voices');
    return response.data;
  }

  /**
   * Create a voice: from audio files, from clips, or from a text description (VoiceDesign).
   */
  async createVoice(params: {
    name: string;
    description?: string;
    creation_source: 'audio' | 'clips' | 'prompt';
    audio_files?: File[];
    audio_file?: File;
    clip_ranges?: AudioClipRange[];
    voice_design_prompt?: string;
    keywords?: string;
    language_code?: string;
    gender?: string;
    image?: File;
  }): Promise<VoiceCreateResponse> {
    const formData = new FormData();
    formData.append('name', params.name);
    if (params.description) {
      formData.append('description', params.description);
    }
    formData.append('creation_source', params.creation_source);
    if (params.keywords) {
      formData.append('keywords', params.keywords);
    }
    if (params.language_code) {
      formData.append('language_code', params.language_code);
    }
    if (params.gender) {
      formData.append('gender', params.gender);
    }
    if (params.image) {
      formData.append('image', params.image);
    }
    if (params.creation_source === 'audio' && params.audio_files?.length) {
      params.audio_files.forEach((file) => formData.append('audio_files', file));
    }
    if (params.creation_source === 'clips') {
      if (params.audio_file) {
        formData.append('audio_file', params.audio_file);
      }
      if (params.clip_ranges?.length) {
        formData.append('clip_ranges', JSON.stringify(params.clip_ranges));
      }
    }
    if (params.creation_source === 'prompt' && params.voice_design_prompt) {
      formData.append('voice_design_prompt', params.voice_design_prompt);
    }

    const response = await this.client.post<VoiceCreateResponse>('/api/v1/voices', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  /**
   * Upload or replace avatar image for a custom voice
   */
  async uploadVoiceImage(voiceId: string, file: File): Promise<VoiceUpdateResponse> {
    const formData = new FormData();
    formData.append('image', file);
    const response = await this.client.put<VoiceUpdateResponse>(
      `/api/v1/voices/${voiceId}/image`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  }

  /**
   * Create a voice from clips (convenience wrapper for createVoice with creation_source=clips).
   */
  async createVoiceFromClips(
    name: string,
    description: string | undefined,
    audioFile: File,
    clipRanges: AudioClipRange[],
    keywords?: string,
    languageCode?: string,
    gender?: string,
    image?: File
  ): Promise<VoiceCreateResponse> {
    return this.createVoice({
      name,
      description,
      creation_source: 'clips',
      audio_file: audioFile,
      clip_ranges: clipRanges,
      keywords,
      language_code: languageCode,
      gender,
      image,
    });
  }

  /**
   * Delete a custom voice
   */
  async deleteVoice(voiceId: string): Promise<void> {
    await this.client.delete(`/api/v1/voices/${voiceId}`);
  }

  /**
   * Update voice details (name and/or description)
   */
  async updateVoice(
    voiceId: string,
    request: VoiceUpdateRequest
  ): Promise<VoiceUpdateResponse> {
    const response = await this.client.put<VoiceUpdateResponse>(
      `/api/v1/voices/${voiceId}`,
      request
    );
    return response.data;
  }

  /**
   * Get voice profile
   */
  async getVoiceProfile(voiceId: string): Promise<VoiceProfileResponse> {
    const response = await this.client.get<VoiceProfileResponse>(
      `/api/v1/voices/${voiceId}/profile`
    );
    return response.data;
  }

  /**
   * Create or update voice profile
   */
  async createOrUpdateVoiceProfile(
    voiceId: string,
    request: VoiceProfileRequest
  ): Promise<VoiceProfileResponse> {
    const response = await this.client.post<VoiceProfileResponse>(
      `/api/v1/voices/${voiceId}/profile`,
      request
    );
    return response.data;
  }

  /**
   * Update voice profile keywords
   */
  async updateVoiceProfileKeywords(
    voiceId: string,
    request: VoiceProfileRequest
  ): Promise<VoiceProfileResponse> {
    const response = await this.client.put<VoiceProfileResponse>(
      `/api/v1/voices/${voiceId}/profile/keywords`,
      request
    );
    return response.data;
  }

  /**
   * Manually generate voice profile
   */
  async generateVoiceProfile(
    voiceId: string,
    request: VoiceProfileRequest
  ): Promise<VoiceProfileResponse> {
    const response = await this.client.post<VoiceProfileResponse>(
      `/api/v1/voices/${voiceId}/profile/generate`,
      request
    );
    return response.data;
  }

  /**
   * Generate podcast script from article URL
   */
  async generatePodcastScript(request: PodcastScriptRequest): Promise<PodcastScriptResponse> {
    const response = await this.client.post<PodcastScriptResponse>(
      '/api/v1/podcast/generate-script',
      request
    );
    return response.data;
  }

  /**
   * Generate podcast audio from script
   */
  async generatePodcastAudio(request: PodcastGenerateRequest): Promise<PodcastGenerateResponse> {
    const response = await this.client.post<PodcastGenerateResponse>(
      '/api/v1/podcast/generate',
      request
    );
    return response.data;
  }

  /**
   * Download generated podcast audio file
   */
  async downloadPodcastAudio(filename: string): Promise<Blob> {
    const response = await this.client.get(`/api/v1/podcast/download/${filename}`, {
      responseType: 'blob',
    });
    return response.data;
  }

  /**
   * List/search saved podcasts
   */
  async listPodcasts(query?: string): Promise<PodcastListResponse> {
    const response = await this.client.get<PodcastListResponse>('/api/v1/podcasts', {
      params: query ? { query } : undefined,
    });
    return response.data;
  }

  /**
   * Delete a saved podcast
   */
  async deletePodcast(podcastId: string): Promise<void> {
    await this.client.delete(`/api/v1/podcasts/${podcastId}`);
  }

  /**
   * Download saved podcast audio by id
   */
  async downloadPodcastById(podcastId: string): Promise<Blob> {
    const response = await this.client.get(`/api/v1/podcasts/${podcastId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  }

  /**
   * Analyze audio file to derive a voice profile
   */
  async analyzeVoiceProfileFromAudio(
    audioFile: File,
    keywords?: string,
    ollamaUrl?: string,
    ollamaModel?: string
  ): Promise<VoiceProfileFromAudioResponse> {
    const formData = new FormData();
    formData.append('audio_file', audioFile);
    if (keywords) formData.append('keywords', keywords);
    if (ollamaUrl) formData.append('ollama_url', ollamaUrl);
    if (ollamaModel) formData.append('ollama_model', ollamaModel);

    const response = await this.client.post<VoiceProfileFromAudioResponse>(
      '/api/v1/voices/profile/analyze-audio',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  }

  /**
   * Apply a full voice profile payload to a voice
   */
  async applyVoiceProfile(voiceId: string, request: VoiceProfileApplyRequest): Promise<VoiceProfileResponse> {
    const response = await this.client.put<VoiceProfileResponse>(`/api/v1/voices/${voiceId}/profile`, request);
    return response.data;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();