/**
 * Main speech generation interface
 */

import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useVoices } from '../hooks/useVoices';
import { useSettings } from '../hooks/useSettings';
import { SpeechSettings } from '../types/api';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Select, MultiSelect } from '../components/Select';
import { AudioPlayer } from '../components/AudioPlayer';
import { Alert } from '../components/Alert';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { SUPPORTED_LANGUAGES } from '../utils/languages';
import { formatVoiceLabel } from '../utils/format';

export function GeneratePage() {
  const { settings } = useSettings();
  const { voices, loading: voicesLoading } = useVoices();
  const { generateSpeech, downloadAudio, loading, error } = useApi();

  const [transcript, setTranscript] = useState('');
  const [selectedSpeakers, setSelectedSpeakers] = useState<string[]>([]);
  const [speechSettings, setSpeechSettings] = useState<SpeechSettings>({
    language: settings.defaultLanguage,
    output_format: settings.defaultOutputFormat,
    sample_rate: settings.defaultSampleRate,
  });
  const [showSettings, setShowSettings] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioFilename, setAudioFilename] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  // Initialize with example transcript
  useEffect(() => {
    if (!transcript) {
      setTranscript(`Speaker 1: Hello, this is a test of the VibeVoice API.
Speaker 2: The API is working correctly.
Speaker 1: This is great news!
Speaker 2: Yes, speech generation is successful.`);
    }
  }, []);

  const handleGenerate = async () => {
    if (!transcript.trim()) {
      setSuccessMessage(null);
      return;
    }

    if (selectedSpeakers.length === 0) {
      setSuccessMessage(null);
      return;
    }

    setAudioUrl(null);
    setAudioFilename(null);
    setSuccessMessage(null);

    const response = await generateSpeech({
      transcript,
      speakers: selectedSpeakers,
      settings: speechSettings,
    });

    if (response && response.audio_url) {
      const fullUrl = `${settings.apiEndpoint}${response.audio_url}`;
      setAudioUrl(fullUrl);
      setAudioFilename(response.audio_url.split('/').pop() || null);
      setSuccessMessage(response.message || 'Speech generated successfully!');
    }
  };

  const handleDownload = async () => {
    if (!audioFilename) return;

    setDownloading(true);
    const blob = await downloadAudio(audioFilename);
    setDownloading(false);

    if (blob) {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = audioFilename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }
  };

  const speakerOptions = voices.map((voice) => ({
    value: voice.name,
    label: formatVoiceLabel(voice),
  }));

  const languageOptions = SUPPORTED_LANGUAGES;

  const formatOptions = [
    { value: 'wav', label: 'WAV' },
  ];

  const sampleRateOptions = [
    { value: '24000', label: '24000 Hz' },
    { value: '44100', label: '44100 Hz' },
    { value: '48000', label: '48000 Hz' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Generate Speech</h1>
        <p className="mt-2 text-gray-600">Convert text to speech using VibeVoice</p>
      </div>

      {error && <Alert type="error" message={error} />}
      {successMessage && <Alert type="success" message={successMessage} />}

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        <div>
          <Input
            label="Transcript"
            multiline
            rows={8}
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Enter transcript with speaker labels (e.g., 'Speaker 1: Hello')"
            required
          />
          <p className="mt-1 text-xs text-gray-500">
            Format: Use "Speaker 1:", "Speaker 2:", etc. to indicate different speakers
          </p>
        </div>

        <div>
          {voicesLoading ? (
            <div className="flex items-center gap-2">
              <LoadingSpinner size="sm" />
              <span className="text-sm text-gray-600">Loading voices...</span>
            </div>
          ) : (
            <MultiSelect
              label="Speakers"
              options={speakerOptions}
              selected={selectedSpeakers}
              onChange={setSelectedSpeakers}
              required
              error={selectedSpeakers.length === 0 && transcript.trim() ? 'At least one speaker is required' : undefined}
            />
          )}
        </div>

        <div>
          <Button
            variant="secondary"
            onClick={() => setShowSettings(!showSettings)}
            className="mb-4"
          >
            {showSettings ? 'Hide' : 'Show'} Advanced Settings
          </Button>

          {showSettings && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
              <Select
                label="Language"
                options={languageOptions}
                value={speechSettings.language}
                onChange={(e) =>
                  setSpeechSettings({ ...speechSettings, language: e.target.value })
                }
              />
              <Select
                label="Output Format"
                options={formatOptions}
                value={speechSettings.output_format}
                onChange={(e) =>
                  setSpeechSettings({ ...speechSettings, output_format: e.target.value })
                }
              />
              <Select
                label="Sample Rate"
                options={sampleRateOptions}
                value={speechSettings.sample_rate.toString()}
                onChange={(e) =>
                  setSpeechSettings({
                    ...speechSettings,
                    sample_rate: parseInt(e.target.value),
                  })
                }
              />
            </div>
          )}
        </div>

        <Button
          variant="primary"
          onClick={handleGenerate}
          isLoading={loading}
          disabled={!transcript.trim() || selectedSpeakers.length === 0 || voicesLoading}
          className="w-full"
        >
          Generate Speech
        </Button>
      </div>

      {audioUrl && (
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <h2 className="text-xl font-semibold text-gray-900">Generated Audio</h2>
          <AudioPlayer src={audioUrl} filename={audioFilename || undefined} />
          <Button
            variant="secondary"
            onClick={handleDownload}
            isLoading={downloading}
            className="w-full"
          >
            Download Audio
          </Button>
        </div>
      )}
    </div>
  );
}