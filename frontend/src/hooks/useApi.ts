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
  PodcastScriptRequest,
  PodcastScriptResponse,
  PodcastGenerateRequest,
  PodcastGenerateResponse,
  VoiceProfileResponse,
  VoiceProfileRequest,
  VoiceUpdateRequest,
  VoiceUpdateResponse,
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
    async (name: string, description: string | undefined, files: File[], keywords?: string): Promise<VoiceCreateResponse | null> => {
      return execute(() => apiClient.createVoice(name, description, files, keywords));
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

  const generatePodcastScript = useCallback(
    async (request: PodcastScriptRequest): Promise<PodcastScriptResponse | null> => {
      return execute(() => apiClient.generatePodcastScript(request));
    },
    [execute]
  );

  const generatePodcastAudio = useCallback(
    async (request: PodcastGenerateRequest): Promise<PodcastGenerateResponse | null> => {
      return execute(() => apiClient.generatePodcastAudio(request));
    },
    [execute]
  );

  const downloadPodcastAudio = useCallback(
    async (filename: string): Promise<Blob | null> => {
      return execute(() => apiClient.downloadPodcastAudio(filename));
    },
    [execute]
  );

  const updateVoice = useCallback(
    async (voiceId: string, request: VoiceUpdateRequest): Promise<VoiceUpdateResponse | null> => {
      return execute(() => apiClient.updateVoice(voiceId, request));
    },
    [execute]
  );

  const getVoiceProfile = useCallback(
    async (voiceId: string): Promise<VoiceProfileResponse | null> => {
      return execute(() => apiClient.getVoiceProfile(voiceId));
    },
    [execute]
  );

  const createOrUpdateVoiceProfile = useCallback(
    async (voiceId: string, request: VoiceProfileRequest): Promise<VoiceProfileResponse | null> => {
      return execute(() => apiClient.createOrUpdateVoiceProfile(voiceId, request));
    },
    [execute]
  );

  const updateVoiceProfileKeywords = useCallback(
    async (voiceId: string, request: VoiceProfileRequest): Promise<VoiceProfileResponse | null> => {
      return execute(() => apiClient.updateVoiceProfileKeywords(voiceId, request));
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
    updateVoice,
    getVoiceProfile,
    createOrUpdateVoiceProfile,
    updateVoiceProfileKeywords,
    generatePodcastScript,
    generatePodcastAudio,
    downloadPodcastAudio,
  };
}