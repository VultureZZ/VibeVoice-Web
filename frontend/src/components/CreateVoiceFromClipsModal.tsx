/**
 * Modal for creating a custom voice by selecting multiple clips from one audio file.
 */
import { useMemo, useRef, useState } from 'react';
import type { AudioClipRange, VoiceCreateResponse } from '../types/api';
import { validateVoiceName, isValidAudioFile } from '../utils/validation';
import { Alert } from './Alert';
import { Button } from './Button';
import { Input } from './Input';
import { Select } from './Select';
import { SUPPORTED_LANGUAGES } from '../utils/languages';

interface CreateVoiceFromClipsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (
    name: string,
    description: string | undefined,
    audioFile: File,
    clipRanges: AudioClipRange[],
    keywords?: string,
    languageCode?: string,
    gender?: string
  ) => Promise<VoiceCreateResponse | null>;
}

export function CreateVoiceFromClipsModal({ isOpen, onClose, onCreate }: CreateVoiceFromClipsModalProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const [voiceName, setVoiceName] = useState('');
  const [voiceDescription, setVoiceDescription] = useState('');
  const [voiceKeywords, setVoiceKeywords] = useState('');
  const [voiceLanguageCode, setVoiceLanguageCode] = useState<string>('');
  const [voiceGender, setVoiceGender] = useState<string>('unknown');

  const [markStart, setMarkStart] = useState<number | null>(null);
  const [markEnd, setMarkEnd] = useState<number | null>(null);
  const [clips, setClips] = useState<AudioClipRange[]>([]);

  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nameValidation = validateVoiceName(voiceName);

  const totalSelectedSeconds = useMemo(
    () => clips.reduce((sum, c) => sum + Math.max(0, c.end_seconds - c.start_seconds), 0),
    [clips]
  );

  const resetAndClose = () => {
    setAudioFile(null);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    setAudioUrl(null);
    setVoiceName('');
    setVoiceDescription('');
    setVoiceKeywords('');
    setVoiceLanguageCode('');
    setVoiceGender('unknown');
    setMarkStart(null);
    setMarkEnd(null);
    setClips([]);
    setError(null);
    onClose();
  };

  const handlePickFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    if (!f) return;
    if (!isValidAudioFile(f)) {
      setError('Please choose a valid audio file');
      return;
    }
    setError(null);
    setAudioFile(f);
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(URL.createObjectURL(f));
    setMarkStart(null);
    setMarkEnd(null);
    setClips([]);
  };

  const getCurrentTime = () => {
    const a = audioRef.current;
    if (!a) return 0;
    return a.currentTime || 0;
  };

  const handleSetStart = () => {
    setMarkStart(getCurrentTime());
  };

  const handleSetEnd = () => {
    setMarkEnd(getCurrentTime());
  };

  const handleAddClip = () => {
    if (markStart === null || markEnd === null) {
      setError('Please mark both start and end before adding a clip');
      return;
    }
    const start = Math.min(markStart, markEnd);
    const end = Math.max(markStart, markEnd);
    if (end - start < 0.5) {
      setError('Clip is too short (minimum 0.5s)');
      return;
    }
    setError(null);
    setClips((prev) => [...prev, { start_seconds: start, end_seconds: end }]);
  };

  const removeClip = (index: number) => {
    setClips((prev) => prev.filter((_, i) => i !== index));
  };

  const handleCreate = async () => {
    if (!audioFile) {
      setError('Please choose an audio file');
      return;
    }
    if (!nameValidation.valid) {
      setError(nameValidation.error || 'Please provide a valid voice name');
      return;
    }
    if (clips.length === 0) {
      setError('Please add at least one clip');
      return;
    }

    setCreating(true);
    setError(null);

    const resp = await onCreate(
      voiceName.trim(),
      voiceDescription.trim() || undefined,
      audioFile,
      clips,
      voiceKeywords.trim() || undefined,
      voiceLanguageCode || undefined,
      voiceGender || undefined
    );

    setCreating(false);
    if (!resp) return;

    if (!resp.success) {
      setError(resp.message || 'Failed to create voice');
      return;
    }

    resetAndClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-semibold text-gray-900">Create Voice from Clips</h2>
          <Button variant="secondary" onClick={resetAndClose} disabled={creating}>
            Close
          </Button>
        </div>

        {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

        <div className="space-y-6">
          <div className="bg-gray-50 border rounded-lg p-4 space-y-4">
            <Input
              label="Voice Name"
              value={voiceName}
              onChange={(e) => setVoiceName(e.target.value)}
              error={voiceName && !nameValidation.valid ? nameValidation.error : undefined}
              required
              placeholder="e.g., My Custom Voice"
            />

            <Input
              label="Description (Optional)"
              multiline
              rows={3}
              value={voiceDescription}
              onChange={(e) => setVoiceDescription(e.target.value)}
              placeholder="Describe this voice..."
            />

            <Input
              label="Keywords (Optional)"
              value={voiceKeywords}
              onChange={(e) => setVoiceKeywords(e.target.value)}
              placeholder="e.g., calm, technical, upbeat (comma-separated)"
              helpText="Used as light context for profiling; the audio drives the voice creation"
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Select
                label="Language (Optional)"
                options={[{ value: '', label: 'Unknown' }, { value: 'in', label: 'Indian' }, ...SUPPORTED_LANGUAGES]}
                value={voiceLanguageCode}
                onChange={(e) => setVoiceLanguageCode(e.target.value)}
              />
              <Select
                label="Gender (Optional)"
                options={[
                  { value: 'unknown', label: 'Unknown' },
                  { value: 'female', label: 'Female' },
                  { value: 'male', label: 'Male' },
                  { value: 'neutral', label: 'Gender-neutral' },
                ]}
                value={voiceGender}
                onChange={(e) => setVoiceGender(e.target.value)}
              />
            </div>

            <details className="rounded border border-gray-200 bg-gray-50 p-3">
              <summary className="cursor-pointer text-sm font-medium text-gray-700">Tips for best quality</summary>
              <ul className="mt-2 list-disc list-inside space-y-1 text-sm text-gray-600">
                <li>5–15 seconds of clear speech (or one clean clip in that range) works best.</li>
                <li>Use a quiet environment; no background music or other voices.</li>
                <li>Normal speech with varied intonation; include a transcript in the voice profile if possible.</li>
                <li>Keep total selected duration under 60 seconds.</li>
              </ul>
            </details>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Audio file</label>
              <input type="file" accept="audio/*" onChange={handlePickFile} disabled={creating} />
              {audioFile && <p className="mt-1 text-xs text-gray-600">{audioFile.name}</p>}
            </div>

            {audioUrl && (
              <div className="space-y-2">
                <audio ref={audioRef} src={audioUrl} controls className="w-full" />
                <div className="flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={handleSetStart} disabled={creating}>
                    Mark start ({markStart !== null ? markStart.toFixed(2) : '—'}s)
                  </Button>
                  <Button variant="secondary" onClick={handleSetEnd} disabled={creating}>
                    Mark end ({markEnd !== null ? markEnd.toFixed(2) : '—'}s)
                  </Button>
                  <Button variant="primary" onClick={handleAddClip} disabled={creating || markStart === null || markEnd === null}>
                    Add clip
                  </Button>
                </div>
                <p className="text-xs text-gray-600">
                  For best results, keep total selected duration between 5–15 seconds (max 60s). Total selected:{' '}
                  {totalSelectedSeconds.toFixed(2)}s.
                </p>
              </div>
            )}
          </div>

          {clips.length > 0 && (
            <div className="bg-white border rounded-lg p-4 space-y-3">
              <h3 className="text-lg font-semibold text-gray-900">Selected clips ({clips.length})</h3>
              <div className="space-y-2">
                {clips.map((c, idx) => (
                  <div key={idx} className="flex items-center justify-between gap-3 p-2 bg-gray-50 rounded border">
                    <div className="text-sm text-gray-900">
                      <span className="font-medium">Clip {idx + 1}:</span> {c.start_seconds.toFixed(2)}s →{' '}
                      {c.end_seconds.toFixed(2)}s ({(c.end_seconds - c.start_seconds).toFixed(2)}s)
                    </div>
                    <button
                      type="button"
                      onClick={() => removeClip(idx)}
                      className="text-red-600 hover:text-red-800 text-sm"
                      disabled={creating}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <Button
            variant="primary"
            onClick={handleCreate}
            isLoading={creating}
            disabled={!audioFile || clips.length === 0 || !nameValidation.valid}
            className="w-full"
          >
            Create Voice
          </Button>
        </div>
      </div>
    </div>
  );
}

