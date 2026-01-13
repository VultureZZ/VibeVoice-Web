/**
 * Card component for displaying voice information.
 */

import { VoiceResponse } from '@/types/api';
import { formatDate } from '@/utils/format';
import { Button } from './Button';

interface VoiceCardProps {
  voice: VoiceResponse;
  onDelete?: (voiceId: string) => void;
  deleting?: boolean;
}

export function VoiceCard({ voice, onDelete, deleting = false }: VoiceCardProps) {
  const isCustom = voice.type === 'custom';

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-gray-900">{voice.name}</h3>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                isCustom
                  ? 'bg-purple-100 text-purple-800'
                  : 'bg-blue-100 text-blue-800'
              }`}
            >
              {voice.type}
            </span>
          </div>
          {voice.description && (
            <p className="mt-1 text-sm text-gray-600">{voice.description}</p>
          )}
          <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
            {voice.created_at && (
              <span>Created: {formatDate(voice.created_at)}</span>
            )}
            {voice.audio_files && voice.audio_files.length > 0 && (
              <span>{voice.audio_files.length} file(s)</span>
            )}
          </div>
        </div>
        {isCustom && onDelete && (
          <div className="ml-4 flex-shrink-0">
            <Button
              variant="danger"
              onClick={() => onDelete(voice.id)}
              disabled={deleting}
              className="text-sm px-3 py-1"
            >
              Delete
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
