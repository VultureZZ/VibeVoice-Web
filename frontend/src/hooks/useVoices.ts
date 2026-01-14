/**
 * Custom hook for voice management with caching
 */

import { useState, useEffect, useCallback } from 'react';
import { VoiceResponse } from '../types/api';
import { useApi } from './useApi';

export function useVoices() {
  const { listVoices: apiListVoices, loading, error } = useApi();
  const [voices, setVoices] = useState<VoiceResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchVoices = useCallback(async () => {
    setIsLoading(true);
    const response = await apiListVoices();
    if (response) {
      setVoices(response.voices);
    }
    setIsLoading(false);
  }, [apiListVoices]);

  useEffect(() => {
    fetchVoices();
  }, [fetchVoices]);

  return {
    voices,
    loading: isLoading || loading,
    error,
    refresh: fetchVoices,
  };
}