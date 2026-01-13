/**
 * Settings interface for storing API endpoint, API key, and default preferences.
 */

import { SpeechSettings } from './api';

export interface AppSettings {
  apiUrl: string;
  apiKey?: string;
  defaultSettings: SpeechSettings;
}

export const DEFAULT_SETTINGS: AppSettings = {
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  apiKey: undefined,
  defaultSettings: {
    language: 'en',
    output_format: 'wav',
    sample_rate: 24000,
  },
};
