/**
 * API client service using Axios.
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  SpeechGenerateRequest,
  SpeechGenerateResponse,
  VoiceListResponse,
  VoiceCreateResponse,
  HealthCheckResponse,
  ErrorResponse,
} from '@/types/api';
import { AppSettings } from '@/types/settings';
import { loadSettings } from './storage';

class ApiClient {
  private client: AxiosInstance;
  private settings: AppSettings;

  constructor() {
    this.settings = loadSettings();
    this.client = axios.create({
      baseURL: this.settings.apiUrl,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for API key
    this.client.interceptors.request.use(
      (config) => {
        const currentSettings = loadSettings();
        if (currentSettings.apiKey) {
          config.headers['X-API-Key'] = currentSettings.apiKey;
        }
        config.baseURL = currentSettings.apiUrl;
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ErrorResponse>) => {
        if (error.response) {
          // Server responded with error status
          const errorMessage =
            error.response.data?.detail ||
            error.response.data?.error ||
            error.message ||
            'An error occurred';
          return Promise.reject(new Error(errorMessage));
        } else if (error.request) {
          // Request was made but no response received
          return Promise.reject(
            new Error('Network error: Unable to connect to the API server')
          );
        } else {
          // Something else happened
          return Promise.reject(error);
        }
      }
    );
  }

  /**
   * Update settings and recreate client.
   */
  updateSettings(settings: AppSettings): void {
    this.settings = settings;
    this.client.defaults.baseURL = settings.apiUrl;
  }

  /**
   * Health check endpoint.
   */
  async healthCheck(): Promise<HealthCheckResponse> {
    const response = await this.client.get<HealthCheckResponse>('/health');
    return response.data;
  }

  /**
   * Generate speech from text.
   */
  async generateSpeech(
    request: SpeechGenerateRequest
  ): Promise<SpeechGenerateResponse> {
    const response = await this.client.post<SpeechGenerateResponse>(
      '/api/v1/speech/generate',
      request
    );
    return response.data;
  }

  /**
   * Download generated audio file.
   */
  async downloadAudio(filename: string): Promise<Blob> {
    const response = await this.client.get(`/api/v1/speech/download/${filename}`, {
      responseType: 'blob',
    });
    return response.data;
  }

  /**
   * List all available voices.
   */
  async listVoices(): Promise<VoiceListResponse> {
    const response = await this.client.get<VoiceListResponse>('/api/v1/voices');
    return response.data;
  }

  /**
   * Create a custom voice from uploaded audio files.
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

    const response = await this.client.post<VoiceCreateResponse>(
      '/api/v1/voices',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  }

  /**
   * Delete a custom voice.
   */
  async deleteVoice(voiceId: string): Promise<void> {
    await this.client.delete(`/api/v1/voices/${voiceId}`);
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
