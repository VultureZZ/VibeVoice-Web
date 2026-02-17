import { useEffect, useMemo, useState } from 'react';
import { useApi } from '../hooks/useApi';
import { Alert } from '../components/Alert';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { RecordingUpload } from '../components/transcripts/RecordingUpload';
import { ProcessingStatus } from '../components/transcripts/ProcessingStatus';
import { SpeakerLabeler } from '../components/transcripts/SpeakerLabeler';
import { TranscriptViewer } from '../components/transcripts/TranscriptViewer';
import { SummaryView } from '../components/transcripts/SummaryView';
import { ExportControls } from '../components/transcripts/ExportControls';
import type { RecordingType, TranscriptItem, TranscriptStatusResponse } from '../types/api';

export function TranscriptsPage() {
  const {
    uploadTranscript,
    getTranscriptStatus,
    getTranscript,
    updateTranscriptSpeakers,
    downloadTranscriptReport,
    loading,
    error,
  } = useApi();
  const [transcriptId, setTranscriptId] = useState<string | null>(null);
  const [status, setStatus] = useState<TranscriptStatusResponse | null>(null);
  const [item, setItem] = useState<TranscriptItem | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!transcriptId) return;
    let stop = false;
    const poll = async () => {
      const s = await getTranscriptStatus(transcriptId);
      if (stop || !s) return;
      setStatus(s);
      if (['complete', 'awaiting_labels', 'failed'].includes(s.status)) {
        const full = await getTranscript(transcriptId);
        if (!stop && full) setItem(full);
      }
    };
    poll();
    const timer = window.setInterval(poll, 3000);
    return () => {
      stop = true;
      window.clearInterval(timer);
    };
  }, [transcriptId, getTranscriptStatus, getTranscript]);

  const startUpload = async (payload: {
    file: File;
    title?: string;
    recordingType: RecordingType;
    language: string;
  }) => {
    setSuccessMessage(null);
    setItem(null);
    setStatus(null);
    const response = await uploadTranscript({
      audioFile: payload.file,
      title: payload.title,
      recordingType: payload.recordingType,
      language: payload.language,
    });
    if (response) {
      setTranscriptId(response.transcript_id);
      setSuccessMessage(response.message);
    }
  };

  const handleProceed = async (labels: { id: string; label: string }[]) => {
    if (!transcriptId) return;
    const result = await updateTranscriptSpeakers(transcriptId, {
      speakers: labels,
      proceed_to_analysis: true,
    });
    if (result) {
      setSuccessMessage(result.message);
      const full = await getTranscript(transcriptId);
      if (full) setItem(full);
    }
  };

  const transcriptTextForCopy = useMemo(() => {
    if (!item?.transcript) return '';
    return item.transcript.map((x) => `${x.speaker_id}: ${x.text}`).join('\n');
  }, [item]);

  const downloadReport = async (format: 'pdf' | 'json') => {
    if (!transcriptId) return;
    const blob = await downloadTranscriptReport(transcriptId, format);
    if (!blob) return;
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${transcriptId}.${format}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const copyTranscript = () => {
    if (!transcriptTextForCopy) return;
    navigator.clipboard.writeText(transcriptTextForCopy);
    setSuccessMessage('Transcript copied to clipboard.');
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Transcripts</h1>
        <p className="mt-2 text-gray-600">
          Upload meetings, calls, voice memos, and interviews for transcription and analysis.
        </p>
      </div>

      {error && <Alert type="error" message={error} />}
      {successMessage && (
        <Alert type="success" message={successMessage} onClose={() => setSuccessMessage(null)} />
      )}

      <RecordingUpload isLoading={loading && !transcriptId} onSubmit={startUpload} />

      {status && status.status !== 'complete' && status.status !== 'awaiting_labels' && (
        <ProcessingStatus status={status} />
      )}

      {status?.status === 'awaiting_labels' && item?.speakers && (
        <SpeakerLabeler speakers={item.speakers} onProceed={handleProceed} isLoading={loading} />
      )}

      {loading && transcriptId && !item ? (
        <div className="flex justify-center py-8">
          <LoadingSpinner size="lg" />
        </div>
      ) : null}

      {item && (
        <>
          <SummaryView analysis={item.analysis} recordingType={item.recording_type} />
          <TranscriptViewer transcript={item.transcript || []} />
          <ExportControls
            onDownloadPdf={() => downloadReport('pdf')}
            onDownloadJson={() => downloadReport('json')}
            onCopyTranscript={copyTranscript}
            isLoading={loading}
          />
        </>
      )}
    </div>
  );
}

