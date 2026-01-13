/**
 * Custom hook for settings management.
 */

import { useState, useEffect, useCallback } from 'react';
import { AppSettings, DEFAULT_SETTINGS } from '@/types/settings';
import { loadSettings, saveSettings } from '@/services/storage';

export function useSettings() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const loadedSettings = loadSettings();
    setSettings(loadedSettings);
    setLoaded(true);
  }, []);

  const updateSettings = useCallback((newSettings: AppSettings) => {
    saveSettings(newSettings);
    setSettings(newSettings);
  }, []);

  const resetSettings = useCallback(() => {
    saveSettings(DEFAULT_SETTINGS);
    setSettings(DEFAULT_SETTINGS);
  }, []);

  return {
    settings,
    updateSettings,
    resetSettings,
    loaded,
  };
}
