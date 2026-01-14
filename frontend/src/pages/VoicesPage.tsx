/**
 * Voice management interface
 */

import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { useVoices } from '../hooks/useVoices';
import { validateVoiceName } from '../utils/validation';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { FileUpload } from '../components/FileUpload';
import { VoiceCard } from '../components/VoiceCard';
import { Alert } from '../components/Alert';
import { LoadingSpinner } from '../components/LoadingSpinner';

export function VoicesPage() {
  const { voices, loading: voicesLoading, refresh } = useVoices();
  const { createVoice, deleteVoice, loading: apiLoading, error: apiError } = useApi();

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [voiceName, setVoiceName] = useState('');
  const [voiceDescription, setVoiceDescription] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [validationFeedback, setValidationFeedback] = useState<string | null>(null);

  const nameValidation = validateVoiceName(voiceName);

  const handleCreateVoice = async () => {
    if (!nameValidation.valid || selectedFiles.length === 0) {
      setErrorMessage('Please provide a valid voice name and at least one audio file');
      return;
    }

    setCreating(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    setValidationFeedback(null);

    const response = await createVoice(
      voiceName.trim(),
      voiceDescription.trim() || undefined,
      selectedFiles
    );

    setCreating(false);

    if (response) {
      if (response.success) {
        setSuccessMessage(response.message);
        setVoiceName('');
        setVoiceDescription('');
        setSelectedFiles([]);
        setShowCreateForm(false);
        refresh();

        // Show validation feedback if present
        if (response.validation_feedback) {
          const feedback = response.validation_feedback;
          const warnings = feedback.warnings.length > 0
            ? `\nWarnings: ${feedback.warnings.join(', ')}`
            : '';
          const recommendations = feedback.recommendations.length > 0
            ? `\nRecommendations: ${feedback.recommendations.join(', ')}`
            : '';
          setValidationFeedback(`Total duration: ${feedback.total_duration_seconds.toFixed(2)}s${warnings}${recommendations}`);
        }
      } else {
        setErrorMessage(response.message || 'Failed to create voice');
      }
    }
  };

  const handleDeleteVoice = async (voiceId: string) => {
    if (!confirm('Are you sure you want to delete this voice? This action cannot be undone.')) {
      return;
    }

    setDeletingId(voiceId);
    const success = await deleteVoice(voiceId);
    setDeletingId(null);

    if (success) {
      setSuccessMessage('Voice deleted successfully');
      refresh();
    }
  };

  const customVoices = voices.filter((v) => v.type === 'custom');
  const defaultVoices = voices.filter((v) => v.type === 'default');

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Voice Management</h1>
          <p className="mt-2 text-gray-600">Manage custom voices and view default voices</p>
        </div>
        <Button
          variant="primary"
          onClick={() => setShowCreateForm(!showCreateForm)}
        >
          {showCreateForm ? 'Cancel' : 'Create Voice'}
        </Button>
      </div>

      {apiError && <Alert type="error" message={apiError} />}
      {errorMessage && <Alert type="error" message={errorMessage} />}
      {successMessage && (
        <Alert
          type="success"
          message={successMessage}
          onClose={() => setSuccessMessage(null)}
        />
      )}
      {validationFeedback && (
        <Alert
          type="info"
          message={validationFeedback}
          onClose={() => setValidationFeedback(null)}
        />
      )}

      {showCreateForm && (
        <div className="bg-white rounded-lg shadow p-6 space-y-6">
          <h2 className="text-xl font-semibold text-gray-900">Create Custom Voice</h2>

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

          <FileUpload
            onFilesChange={setSelectedFiles}
            error={selectedFiles.length === 0 ? 'At least one audio file is required' : undefined}
          />

          <Button
            variant="primary"
            onClick={handleCreateVoice}
            isLoading={creating || apiLoading}
            disabled={!nameValidation.valid || selectedFiles.length === 0}
            className="w-full"
          >
            Create Voice
          </Button>
        </div>
      )}

      <div className="space-y-6">
        {voicesLoading ? (
          <div className="flex justify-center items-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : (
          <>
            {customVoices.length > 0 && (
              <div>
                <h2 className="text-2xl font-semibold text-gray-900 mb-4">Custom Voices ({customVoices.length})</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {customVoices.map((voice) => (
                    <VoiceCard
                      key={voice.id}
                      voice={voice}
                      onDelete={handleDeleteVoice}
                      isDeleting={deletingId === voice.id}
                    />
                  ))}
                </div>
              </div>
            )}

            {defaultVoices.length > 0 && (
              <div>
                <h2 className="text-2xl font-semibold text-gray-900 mb-4">
                  Default Voices ({defaultVoices.length})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {defaultVoices.map((voice) => (
                    <VoiceCard key={voice.id} voice={voice} />
                  ))}
                </div>
              </div>
            )}

            {voices.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                <p>No voices available</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}