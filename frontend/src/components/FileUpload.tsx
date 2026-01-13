/**
 * File upload component for voice creation.
 */

import { useRef, useState } from 'react';
import { validateAudioFiles } from '@/utils/validation';
import { formatFileSize } from '@/utils/format';
import { Button } from './Button';
import { Alert } from './Alert';

interface FileUploadProps {
  files: File[];
  onChange: (files: File[]) => void;
  maxFiles?: number;
  className?: string;
}

export function FileUpload({
  files,
  onChange,
  maxFiles,
  className = '',
}: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const handleFiles = (newFiles: FileList | null) => {
    if (!newFiles || newFiles.length === 0) return;

    const fileArray = Array.from(newFiles);
    const validation = validateAudioFiles(fileArray);

    if (validation.valid) {
      const updatedFiles = maxFiles
        ? [...files, ...fileArray].slice(0, maxFiles)
        : [...files, ...fileArray];
      onChange(updatedFiles);
      setErrors([]);
    } else {
      setErrors(validation.errors);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
  };

  const removeFile = (index: number) => {
    const newFiles = files.filter((_, i) => i !== index);
    onChange(newFiles);
  };

  return (
    <div className={className}>
      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          dragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="audio/*"
          onChange={handleChange}
          className="hidden"
        />
        <div className="space-y-2">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <div className="text-sm text-gray-600">
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="font-medium text-blue-600 hover:text-blue-500"
            >
              Click to upload
            </button>{' '}
            or drag and drop
          </div>
          <p className="text-xs text-gray-500">Audio files (WAV, MP3, M4A, etc.)</p>
        </div>
      </div>

      {errors.length > 0 && (
        <div className="mt-4">
          <Alert type="error" message={errors.join(', ')} />
        </div>
      )}

      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          <h4 className="text-sm font-medium text-gray-700">
            Selected Files ({files.length})
          </h4>
          <ul className="space-y-2">
            {files.map((file, index) => (
              <li
                key={`${file.name}-${index}`}
                className="flex items-center justify-between bg-gray-50 rounded-md p-3"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  className="ml-4 text-red-600 hover:text-red-800 focus:outline-none"
                  aria-label={`Remove ${file.name}`}
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
