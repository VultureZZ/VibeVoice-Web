/**
 * Main speech generation interface.
 */

import { useState, useEffect } from 'react';
import { useSettings } from '@/hooks/useSettings';
import { useVoices } from '@/hooks/useVoices';
import { apiClient } from '@/services/api';
import { SpeechGenerateRequest } from '@/types/api';
import { Button } from '@/components/Button';
import { Input } from '@/components/Input';
import { Select } from '@/components/Select';
import { AudioPlayer } from '@/components/AudioPlayer';
import { Alert } from '@/components/Alert';
import { LoadingSpinner } from '@/components/LoadingSpinner';

export function GeneratePage() {
  const { settings } = useSettings();
  const { voices, loading: voicesLoading } = useVoices();
  const [transcript, setTranscript] = useState('');
  const [selectedSpeakers, setSelectedSpeakers] = useState<string[]>([]);
  const [language, setLanguage] = useState(settings.defaultSettings.language);
  const [outputFormat, setOutputFormat] = useState(settings.defaultSettings.output_format);
  const [sampleRate, setSampleRate] = useState(settings.defaultSettings.sample_rate);
  const [showSettings, setShowSettings] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    setLanguage(settings.defaultSettings.language);
    setOutputFormat(settings.defaultSettings.output_format);
    setSampleRate(settings.defaultSettings.sample_rate);
  }, [settings]);

  const handleGenerate = async () => {
    if (!transcript.trim()) {
      setError('Transcript is required');
      return;
    }
    if (selectedSpeakers.length === 0) {
      setError('At least one speaker must be selected');
      return;
    }

    setGenerating(true);
    setError(null);
    setSuccess(null);
    setAudioUrl(null);

    try {
      const request: SpeechGenerateRequest = {
        transcript,
        speakers: selectedSpeakers,
        settings: {
          language,
          output_format: outputFormat,
          sample_rate: sampleRate,
        },
      };

      const response = await apiClient.generateSpeech(request);
      setSuccess(response.message);
      
      if (response.audio_url) {
        const fullAudioUrl = `${settings.apiUrl}${response.audio_url}`;
        setAudioUrl(fullAudioUrl);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to generate speech';
      setError(message);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async () => {
    if (!audioUrl) return;

    try {
      const filename = audioUrl.split('/').pop() || 'audio.wav';
      const blob = await apiClient.downloadAudio(filename);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to download audio';
      setError(message);
    }
  };

  const speakerOptions = voices.map((voice) => ({
    value: voice.name,
    label: voice.name,
  }));

  const languageOptions = [
    { value: 'en', label: 'English' },
    { value: 'zh', label: 'Chinese' },
  ];

  const sampleRateOptions = [
    { value: '16000', label: '16 kHz' },
    { value: '24000', label: '24 kHz' },
    { value: '44100', label: '44.1 kHz' },
    { value: '48000', label: '48 kHz' },
  ];

  return (
    <div className="px-4 sm:px-0">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Generate Speech</h1>
        <p className="mt-2 text-sm text-gray-600">
          Convert text to speech using VibeVoice
        </p>
      </div>

      {error && (
        <div className="mb-6">
          <Alert type="error" message={error} onClose={() => setError(null)} />
        </div>
      )}

      {success && (
        <div className="mb-6">
          <Alert type="success" message={success} onClose={() => setSuccess(null)} />
        </div>
      )}

      <div className="bg-white shadow rounded-lg">
        <div className="p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Transcript
            </label>
            <Input
              textarea
              rows={10}
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Speaker 1: Hello, this is a test.&#10;Speaker 2: The API is working correctly."
              className="font-mono text-sm"
            />
            <p className="mt-2 text-sm text-gray-500">
              Format: Speaker 1: text, Speaker 2: text, etc.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Speakers (Select {selectedSpeakers.length > 0 ? selectedSpeakers.length : 'one or more'})
            </label>
            {voicesLoading ? (
              <LoadingSpinner />
            ) : (
              <Select
                multiple
                value={selectedSpeakers.join(',')}
                onChange={(e) => {
                  const values = Array.from(
                    e.target.selectedOptions,
                    (option) => option.value
                  );
                  setSelectedSpeakers(values);
                }}
                options={speakerOptions}
              />
            )}
            <p className="mt-2 text-sm text-gray-500">
              Select speakers matching the transcript format (Speaker 1, Speaker 2, etc.)
            </p>
          </div>

          <div>
            <button
              type="button"
              onClick={() => setShowSettings(!showSettings)}
              className="text-sm font-medium text-blue-600 hover:text-blue-500"
            >
              {showSettings ? 'Hide' : 'Show'} Advanced Settings
            </button>
            {showSettings && (
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
                <Select
                  label="Language"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  options={languageOptions}
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Output Format
                  </label>
                  <Input
                    type="text"
                    value={outputFormat}
                    onChange={(e) => setOutputFormat(e.target.value)}
                    disabled
                    className="bg-gray-100"
                  />
                </div>
                <Select
                  label="Sample Rate"
                  value={sampleRate.toString()}
                  onChange={(e) => setSampleRate(parseInt(e.target.value, 10))}
                  options={sampleRateOptions}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="primary"
              onClick={handleGenerate}
              loading={generating}
              disabled={!transcript.trim() || selectedSpeakers.length === 0}
              className="w-full sm:w-auto"
            >
              Generate Speech
            </Button>
          </div>

          {audioUrl && (
            <div className="space-y-4 border-t pt-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Generated Audio
                </h3>
                <AudioPlayer src={audioUrl} />
              </div>
              <div>
                <Button variant="secondary" onClick={handleDownload}>
                  Download Audio
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
