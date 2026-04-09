/**
 * Play a short generated speech sample for a voice (optionally styled via voice profile).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { apiClient } from '../services/api';
import { useSettings } from '../hooks/useSettings';
import type { VoiceResponse } from '../types/api';
import { VOICE_SAMPLE_TRANSCRIPT } from '../utils/voiceSample';

const SAMPLE_PLAY_EVENT = 'audiomesh-voice-sample-play';

interface VoiceSampleButtonProps {
  voice: VoiceResponse;
  /** Load profile and return a style string; may fetch from API. */
  fetchProfileInstruction?: (voiceId: string) => Promise<string | undefined>;
}

function SpeakerWaveIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <path
        d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"
        fill="currentColor"
      />
      <path
        d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"
        fill="currentColor"
      />
      <path
        d="M19 11h2c0 4.97-4.03 9-9 9v-2c3.87 0 7-3.13 7-7z"
        fill="currentColor"
        opacity="0.45"
      />
      <path
        d="M21 11h2c0 6.08-4.92 11-11 11v-2c4.97 0 9-4.03 9-9z"
        fill="currentColor"
        opacity="0.25"
      />
    </svg>
  );
}

export function VoiceSampleButton({ voice, fetchProfileInstruction }: VoiceSampleButtonProps) {
  const { settings } = useSettings();
  const languageCode = (voice.language_code?.trim() || settings.defaultLanguage || 'en').trim();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  const cleanupPlayback = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
    setPlaying(false);
  }, []);

  useEffect(() => {
    return () => cleanupPlayback();
  }, [cleanupPlayback]);

  useEffect(() => {
    const onOtherPlay = (ev: Event) => {
      const e = ev as CustomEvent<string>;
      if (e.detail !== voice.id) {
        cleanupPlayback();
      }
    };
    document.addEventListener(SAMPLE_PLAY_EVENT, onOtherPlay as EventListener);
    return () => document.removeEventListener(SAMPLE_PLAY_EVENT, onOtherPlay as EventListener);
  }, [voice.id, cleanupPlayback]);

  const handleClick = async () => {
    setError(null);

    if (playing && audioRef.current) {
      cleanupPlayback();
      return;
    }

    if (busy) return;

    document.dispatchEvent(new CustomEvent(SAMPLE_PLAY_EVENT, { detail: voice.id }));

    setBusy(true);
    try {
      let styleInstruction: string | undefined;
      if (fetchProfileInstruction) {
        styleInstruction = await fetchProfileInstruction(voice.id);
      }

      const speakerInstructions = styleInstruction?.trim()
        ? [styleInstruction.trim()]
        : undefined;

      const response = await apiClient.generateSpeech({
        transcript: VOICE_SAMPLE_TRANSCRIPT,
        speakers: [voice.name],
        speaker_instructions:
          speakerInstructions && speakerInstructions.length === 1 ? speakerInstructions : undefined,
        settings: {
          language: languageCode || 'en',
          output_format: 'wav',
          sample_rate: 24000,
        },
      });

      if (!response.success || !response.audio_url) {
        throw new Error(response.message || 'Could not generate sample');
      }

      const filename = response.audio_url.split('/').pop();
      if (!filename) throw new Error('Invalid audio URL');

      const blob = await apiClient.downloadAudio(filename);
      const url = URL.createObjectURL(blob);
      objectUrlRef.current = url;

      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => cleanupPlayback();
      audio.onerror = () => {
        setError('Playback failed');
        cleanupPlayback();
      };

      setPlaying(true);
      await audio.play();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Sample failed';
      setError(msg);
      cleanupPlayback();
    } finally {
      setBusy(false);
    }
  };

  const title = playing ? 'Stop sample' : busy ? 'Generating sample…' : 'Play short sample';

  return (
    <span className="inline-flex flex-col items-start gap-0.5">
      <button
        type="button"
        onClick={() => void handleClick()}
        disabled={busy}
        title={title}
        aria-label={title}
        className={`inline-flex items-center justify-center rounded-full p-1.5 border transition-colors ${
          playing
            ? 'border-primary-600 bg-primary-50 text-primary-700'
            : 'border-gray-300 bg-white text-gray-600 hover:bg-gray-50 hover:border-gray-400'
        } disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {busy ? (
          <span className="w-[18px] h-[18px] border-2 border-gray-300 border-t-primary-600 rounded-full animate-spin" />
        ) : (
          <SpeakerWaveIcon className={playing ? 'text-primary-700' : 'text-gray-600'} />
        )}
      </button>
      {error && (
        <span className="text-[10px] text-red-600 max-w-[140px] leading-tight" title={error}>
          {error}
        </span>
      )}
    </span>
  );
}
