/**
 * Commercial vs editorial labels in ad_segments (LLM sometimes marks "News Segment" as an ad).
 * Keep in sync with src/vibevoice/services/ad_scan_segment_utils.py
 */
import type { AdSegmentItem } from '../types/api';

const EDITORIAL_LABEL_SUBSTRINGS = [
  'news segment',
  'main content',
  'editorial',
  'episode content',
  'story segment',
  'discussion segment',
  'interview segment',
  'host segment',
  'cold open',
] as const;

const EDITORIAL_LABELS_EXACT = new Set(['news', 'editorial']);

export function isCommercialAdSegment(seg: AdSegmentItem): boolean {
  const L = (seg.label || '').trim().toLowerCase();
  if (!L) return true;
  if (EDITORIAL_LABELS_EXACT.has(L)) return false;
  for (const s of EDITORIAL_LABEL_SUBSTRINGS) {
    if (L.includes(s)) return false;
  }
  return true;
}

export function filterCommercialAdSegments(segs: AdSegmentItem[]): AdSegmentItem[] {
  return segs.filter(isCommercialAdSegment);
}
