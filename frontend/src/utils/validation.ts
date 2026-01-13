/**
 * Validation utility functions.
 */

/**
 * Validate API endpoint URL.
 */
export function validateApiUrl(url: string): { valid: boolean; error?: string } {
  if (!url || url.trim() === '') {
    return { valid: false, error: 'API URL is required' };
  }

  try {
    const urlObj = new URL(url);
    if (!['http:', 'https:'].includes(urlObj.protocol)) {
      return { valid: false, error: 'API URL must use http:// or https://' };
    }
    return { valid: true };
  } catch {
    return { valid: false, error: 'Invalid URL format' };
  }
}

/**
 * Allowed audio file extensions.
 */
export const ALLOWED_AUDIO_EXTENSIONS = [
  '.wav',
  '.mp3',
  '.m4a',
  '.flac',
  '.ogg',
  '.aac',
];

/**
 * Allowed audio MIME types.
 */
export const ALLOWED_AUDIO_TYPES = [
  'audio/wav',
  'audio/wave',
  'audio/x-wav',
  'audio/mpeg',
  'audio/mp3',
  'audio/mp4',
  'audio/m4a',
  'audio/flac',
  'audio/ogg',
  'audio/aac',
];

/**
 * Maximum file size (100 MB).
 */
export const MAX_FILE_SIZE = 100 * 1024 * 1024;

/**
 * Validate audio file type.
 */
export function validateAudioFileType(file: File): { valid: boolean; error?: string } {
  const extension = '.' + file.name.split('.').pop()?.toLowerCase();
  const isValidExtension = ALLOWED_AUDIO_EXTENSIONS.includes(extension);
  const isValidMimeType =
    ALLOWED_AUDIO_TYPES.some((type) => file.type.includes(type)) ||
    file.type === '';

  if (!isValidExtension && !isValidMimeType) {
    return {
      valid: false,
      error: `Invalid file type. Allowed: ${ALLOWED_AUDIO_EXTENSIONS.join(', ')}`,
    };
  }

  return { valid: true };
}

/**
 * Validate audio file size.
 */
export function validateAudioFileSize(file: File): { valid: boolean; error?: string } {
  if (file.size > MAX_FILE_SIZE) {
    return {
      valid: false,
      error: `File size exceeds maximum of ${MAX_FILE_SIZE / 1024 / 1024} MB`,
    };
  }
  return { valid: true };
}

/**
 * Validate multiple audio files.
 */
export function validateAudioFiles(
  files: File[]
): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (files.length === 0) {
    errors.push('At least one audio file is required');
  }

  files.forEach((file, index) => {
    const typeValidation = validateAudioFileType(file);
    if (!typeValidation.valid) {
      errors.push(`${file.name}: ${typeValidation.error}`);
    }

    const sizeValidation = validateAudioFileSize(file);
    if (!sizeValidation.valid) {
      errors.push(`${file.name}: ${sizeValidation.error}`);
    }
  });

  return {
    valid: errors.length === 0,
    errors,
  };
}
