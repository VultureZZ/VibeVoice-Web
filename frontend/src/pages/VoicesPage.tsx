/**
 * Voice management interface
 */

import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useVoices } from '../hooks/useVoices';
import { validateVoiceName } from '../utils/validation';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { FileUpload } from '../components/FileUpload';
import { VoiceCard } from '../components/VoiceCard';
import { VoiceProfileModal } from '../components/VoiceProfileModal';
import { Alert } from '../components/Alert';
import { LoadingSpinner } from '../components/LoadingSpinner';

export function VoicesPage() {
  const { voices, loading: voicesLoading, refresh } = useVoices();
  const {
    createVoice,
    deleteVoice,
    updateVoice,
    getVoiceProfile,
    createOrUpdateVoiceProfile,
    updateVoiceProfileKeywords,
    generateVoiceProfile,
    loading: apiLoading,
    error: apiError,
  } = useApi();

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [voiceName, setVoiceName] = useState('');
  const [voiceDescription, setVoiceDescription] = useState('');
  const [voiceKeywords, setVoiceKeywords] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [profileModalVoiceId, setProfileModalVoiceId] = useState<string | null>(null);
  const [voiceProfiles, setVoiceProfiles] = useState<Record<string, boolean>>({});
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
      selectedFiles,
      voiceKeywords.trim() || undefined
    );

    setCreating(false);

    if (response) {
      if (response.success) {
        setSuccessMessage(response.message);
        setVoiceName('');
        setVoiceDescription('');
        setVoiceKeywords('');
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

  const handleEditVoice = (voiceId: string) => {
    const voice = voices.find((v) => v.id === voiceId);
    if (voice) {
      setEditingId(voiceId);
      setEditName(voice.name);
      setEditDescription(voice.description || '');
    }
  };

  const handleSaveEdit = async () => {
    if (!editingId) return;

    const response = await updateVoice(editingId, {
      name: editName.trim() || undefined,
      description: editDescription.trim() || undefined,
    });

    if (response && response.success) {
      setSuccessMessage('Voice updated successfully');
      setEditingId(null);
      setEditName('');
      setEditDescription('');
      refresh();
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditName('');
    setEditDescription('');
  };

  // Load profile status for custom voices
  useEffect(() => {
    const loadProfiles = async () => {
      const profiles: Record<string, boolean> = {};
      for (const voice of voices.filter((v) => v.type === 'custom')) {
        try {
          const response = await getVoiceProfile(voice.id);
          profiles[voice.id] = !!(response && response.profile);
        } catch {
          profiles[voice.id] = false;
        }
      }
      setVoiceProfiles(profiles);
    };

    if (voices.length > 0) {
      loadProfiles();
    }
  }, [voices, getVoiceProfile]);

  const handleViewProfile = (voiceId: string) => {
    setProfileModalVoiceId(voiceId);
  };

  const handleUpdateProfileKeywords = async (voiceId: string, keywords: string[]) => {
    // Try to update keywords first, if that fails, create profile
    let response = await updateVoiceProfileKeywords(voiceId, { keywords });
    if (!response || !response.profile) {
      // If update failed, try creating profile
      response = await createOrUpdateVoiceProfile(voiceId, { keywords });
    }
    if (response && response.profile) {
      setVoiceProfiles((prev) => ({ ...prev, [voiceId]: true }));
      return response;
    }
    return null;
  };

  const handleGenerateProfile = async (voiceId: string, keywords: string[]) => {
    const response = await generateVoiceProfile(voiceId, { keywords: keywords.length > 0 ? keywords : undefined });
    if (response && response.profile) {
      setVoiceProfiles((prev) => ({ ...prev, [voiceId]: true }));
      return response;
    }
    return null;
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

          <Input
            label="Keywords (Optional)"
            value={voiceKeywords}
            onChange={(e) => setVoiceKeywords(e.target.value)}
            placeholder="e.g., Donald Trump, President (comma-separated)"
            helpText="Enter keywords to help identify unique speech patterns (e.g., person's name)"
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
                      onEdit={handleEditVoice}
                      onViewProfile={handleViewProfile}
                      isDeleting={deletingId === voice.id}
                      hasProfile={voiceProfiles[voice.id]}
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

      {editingId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Edit Voice</h2>

            <Input
              label="Voice Name"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              required
              placeholder="e.g., My Custom Voice"
            />

            <Input
              label="Description (Optional)"
              multiline
              rows={3}
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              placeholder="Describe this voice..."
              className="mt-4"
            />

            <div className="flex gap-3 mt-6">
              <Button
                variant="primary"
                onClick={handleSaveEdit}
                isLoading={apiLoading}
                className="flex-1"
              >
                Save
              </Button>
              <Button
                variant="secondary"
                onClick={handleCancelEdit}
                disabled={apiLoading}
                className="flex-1"
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {profileModalVoiceId && (
        <VoiceProfileModal
          voiceId={profileModalVoiceId}
          voiceName={voices.find((v) => v.id === profileModalVoiceId)?.name || 'Unknown'}
          isOpen={!!profileModalVoiceId}
          onClose={() => setProfileModalVoiceId(null)}
          onGetProfile={getVoiceProfile}
          onUpdateProfile={handleUpdateProfileKeywords}
          onGenerateProfile={handleGenerateProfile}
        />
      )}
    </div>
  );
}