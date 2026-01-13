/**
 * Custom hook that wraps API client with loading/error states.
 */

import { useState, useCallback } from 'react';
import { apiClient } from '@/services/api';
import { AppSettings } from '@/types/settings';

interface UseApiReturn {
  loading: boolean;
  error: string | null;
  clearError: () => void;
  api: typeof apiClient;
}

export function useApi(): UseApiReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Update API client settings when needed
  const updateApiSettings = useCallback((settings: AppSettings) => {
    apiClient.updateSettings(settings);
  }, []);

  return {
    loading,
    error,
    clearError,
    api: apiClient,
  };
}
