/**
 * Custom hook that wraps API client with loading/error states
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../services/api';
import {
  SpeechGenerateRequest,
  SpeechGenerateResponse,
  VoiceListResponse,
  VoiceCreateResponse,
  HealthCheckResponse,
} from '../types/api';

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(
    async <T,>(fn: () => Promise<T>): Promise<T | null> => {
      setLoading(true);
      setError(null);
      try {
        const result = await fn();
        return result;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
        setError(errorMessage);
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const healthCheck = useCallback(async (): Promise<HealthCheckResponse | null> => {
    return execute(() => apiClient.healthCheck());
  }, [execute]);

  const generateSpeech = useCallback(
    async (request: SpeechGenerateRequest): Promise<SpeechGenerateResponse | null> => {
      return execute(() => apiClient.generateSpeech(request));
    },
    [execute]
  );

  const downloadAudio = useCallback(
    async (filename: string): Promise<Blob | null> => {
      return execute(() => apiClient.downloadAudio(filename));
    },
    [execute]
  );

  const listVoices = useCallback(async (): Promise<VoiceListResponse | null> => {
    return execute(() => apiClient.listVoices());
  }, [execute]);

  const createVoice = useCallback(
    async (name: string, description: string | undefined, files: File[]): Promise<VoiceCreateResponse | null> => {
      return execute(() => apiClient.createVoice(name, description, files));
    },
    [execute]
  );

  const deleteVoice = useCallback(
    async (voiceId: string): Promise<boolean> => {
      const result = await execute(() => apiClient.deleteVoice(voiceId));
      return result !== null;
    },
    [execute]
  );

  return {
    loading,
    error,
    healthCheck,
    generateSpeech,
    downloadAudio,
    listVoices,
    createVoice,
    deleteVoice,
  };
}