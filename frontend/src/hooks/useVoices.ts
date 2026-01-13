/**
 * Custom hook for voice management with cached data.
 */

import { useState, useEffect, useCallback } from 'react';
import { VoiceResponse } from '@/types/api';
import { apiClient } from '@/services/api';

export function useVoices() {
  const [voices, setVoices] = useState<VoiceResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchVoices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.listVoices();
      setVoices(response.voices);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch voices';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVoices();
  }, [fetchVoices]);

  return {
    voices,
    loading,
    error,
    refresh: fetchVoices,
  };
}
