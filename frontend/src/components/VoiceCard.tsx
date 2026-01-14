/**
 * Card component for displaying voice information
 */

import { VoiceResponse } from '../types/api';
import { formatDate } from '../utils/format';
import { Button } from './Button';

interface VoiceCardProps {
  voice: VoiceResponse;
  onDelete?: (voiceId: string) => void;
  isDeleting?: boolean;
}

export function VoiceCard({ voice, onDelete, isDeleting }: VoiceCardProps) {
  const isCustom = voice.type === 'custom';

  return (
    <div className="border rounded-lg p-4 bg-white shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-lg font-semibold text-gray-900">{voice.name}</h3>
            <span
              className={`px-2 py-1 text-xs font-medium rounded ${
                isCustom
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {voice.type}
            </span>
          </div>

          {voice.description && (
            <p className="text-sm text-gray-600 mb-2">{voice.description}</p>
          )}

          <div className="flex flex-wrap gap-4 text-xs text-gray-500">
            <span>ID: {voice.id}</span>
            {voice.created_at && (
              <span>Created: {formatDate(voice.created_at)}</span>
            )}
            {voice.audio_files && voice.audio_files.length > 0 && (
              <span>{voice.audio_files.length} file(s)</span>
            )}
          </div>
        </div>

        {isCustom && onDelete && (
          <Button
            variant="danger"
            onClick={() => onDelete(voice.id)}
            isLoading={isDeleting}
            className="ml-4"
          >
            Delete
          </Button>
        )}
      </div>
    </div>
  );
}