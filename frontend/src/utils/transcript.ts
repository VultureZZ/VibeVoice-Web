import type { TranscriptSpeakerSegment } from '../types/api';

const SENTENCE_END = /[.!?]\s*$/;

/**
 * Merges consecutive transcript segments from the same speaker into
 * sentence-level chunks. Reduces fragmentation from Whisper's phrase-level output.
 */
export function mergeTranscriptSegments(
  segments: TranscriptSpeakerSegment[]
): TranscriptSpeakerSegment[] {
  if (!segments.length) return [];

  const merged: TranscriptSpeakerSegment[] = [];
  let acc: TranscriptSpeakerSegment | null = null;

  for (const seg of segments) {
    const text = (seg.text || '').trim();
    if (!text) continue;

    const sameSpeaker = acc && acc.speaker_id === seg.speaker_id;
    const endsSentence = SENTENCE_END.test(text);

    if (acc && sameSpeaker) {
      acc = {
        ...acc,
        text: `${acc.text} ${text}`.trim(),
        end_ms: seg.end_ms,
        confidence: (acc.confidence + seg.confidence) / 2,
      };
      if (endsSentence) {
        merged.push(acc);
        acc = null;
      }
    } else {
      if (acc) merged.push(acc);
      acc = { ...seg, text };
    }
  }
  if (acc) merged.push(acc);

  return merged;
}
