/**
 * LocalStorage utilities for persisting settings.
 */

import { AppSettings, DEFAULT_SETTINGS } from '@/types/settings';

const SETTINGS_KEY = 'vibevoice_settings';

/**
 * Load settings from localStorage.
 */
export function loadSettings(): AppSettings {
  try {
    const stored = localStorage.getItem(SETTINGS_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Merge with defaults to handle missing fields
      return {
        ...DEFAULT_SETTINGS,
        ...parsed,
        defaultSettings: {
          ...DEFAULT_SETTINGS.defaultSettings,
          ...parsed.defaultSettings,
        },
      };
    }
  } catch (error) {
    console.error('Failed to load settings from localStorage:', error);
  }
  return DEFAULT_SETTINGS;
}

/**
 * Save settings to localStorage.
 */
export function saveSettings(settings: AppSettings): void {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch (error) {
    console.error('Failed to save settings to localStorage:', error);
    throw error;
  }
}

/**
 * Clear settings from localStorage.
 */
export function clearSettings(): void {
  try {
    localStorage.removeItem(SETTINGS_KEY);
  } catch (error) {
    console.error('Failed to clear settings from localStorage:', error);
  }
}
