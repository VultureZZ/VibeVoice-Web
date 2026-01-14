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
   * Create a custom voice
   */
  async createVoice(
    name: string,
    description: string | undefined,
    files: File[]
  ): Promise<VoiceCreateResponse> {
    const formData = new FormData();
    formData.append('name', name);
    if (description) {
      formData.append('description', description);
    }
    files.forEach((file) => {
      formData.append('audio_files', file);
    });

    const response = await this.client.post<VoiceCreateResponse>('/api/v1/voices', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  /**
   * Delete a custom voice
   */
  async deleteVoice(voiceId: string): Promise<void> {
    await this.client.delete(`/api/v1/voices/${voiceId}`);
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
}

// Export singleton instance
export const apiClient = new ApiClient();