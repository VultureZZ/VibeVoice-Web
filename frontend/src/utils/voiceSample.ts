/**
 * Short transcript and profile helpers for voice preview playback on the Voices page.
 */

import type { VoiceProfile } from '../types/api';

/** Kept concise for roughly 5–10 seconds of audio with typical TTS pacing. */
export const VOICE_SAMPLE_TRANSCRIPT = `Speaker 1: Short voice sample. Natural pacing and clear delivery for your projects.`;

const MAX_STYLE_INSTRUCTION_CHARS = 1800;

/**
 * Build a single style instruction string from stored profile fields for TTS `speaker_instructions`.
 */
export function buildProfileStyleInstruction(profile: VoiceProfile | undefined | null): string | undefined {
  if (!profile) return undefined;

  const parts: string[] = [];

  if (profile.profile_text?.trim()) {
    parts.push(profile.profile_text.trim());
  } else {
    if (profile.cadence?.trim()) parts.push(`Cadence: ${profile.cadence.trim()}`);
    if (profile.tone?.trim()) parts.push(`Tone: ${profile.tone.trim()}`);
    if (profile.vocabulary_style?.trim()) parts.push(`Vocabulary: ${profile.vocabulary_style.trim()}`);
    if (profile.sentence_structure?.trim()) parts.push(`Sentence style: ${profile.sentence_structure.trim()}`);
    if (profile.unique_phrases?.length) {
      const phrases = profile.unique_phrases.map((p) => p.trim()).filter(Boolean).slice(0, 8);
      if (phrases.length) parts.push(`Typical phrases: ${phrases.join('; ')}`);
    }
    if (profile.keywords?.length) {
      const kw = profile.keywords.map((k) => k.trim()).filter(Boolean).slice(0, 12);
      if (kw.length) parts.push(`Context: ${kw.join(', ')}`);
    }
  }

  if (parts.length === 0) return undefined;

  let combined = parts.join('\n');
  if (combined.length > MAX_STYLE_INSTRUCTION_CHARS) {
    combined = `${combined.slice(0, MAX_STYLE_INSTRUCTION_CHARS).trimEnd()}…`;
  }

  return combined;
}
