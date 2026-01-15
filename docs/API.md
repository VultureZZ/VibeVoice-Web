# VibeVoice API Reference

This document describes the REST API exposed by the FastAPI backend.

- **Base URL**: `http://localhost:8000`
- **API version prefix**: `/api/v1`
- **Interactive OpenAPI**: `http://localhost:8000/docs` (no auth / no rate-limit)

## Authentication

API key auth is controlled by the `API_KEY` environment variable:

- If **`API_KEY` is unset/empty**, all requests are accepted (even with no key).
- If **`API_KEY` is set**, every request (except `/health`, `/docs`, `/openapi.json`, `/redoc`) must include an API key:
  - Header: `X-API-Key: <key>`
  - Or query param: `?api_key=<key>`

## Rate limiting

Rate limiting is **per API key** (or `"anonymous"` if no key is provided) and is configured by `RATE_LIMIT_PER_MINUTE` (default `100`).

- Responses include:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
- On limit exceeded you’ll receive **HTTP 429** with:
  - `Retry-After: 60`

## Endpoints

### Health / Root

- `GET /health` (no auth / no rate-limit)
- `GET /` (subject to auth / rate-limit)

### Speech

- `POST /api/v1/speech/generate`
  - Body (JSON): `{ transcript: string, speakers: string[], settings?: { language, output_format, sample_rate } }`
  - Notes:
    - The backend currently **does not apply `settings` to VibeVoice inference**; generation uses VibeVoice defaults.
  - Returns: `{ success, message, audio_url, file_path }`

- `WS /api/v1/speech/realtime`
  - Description: **Realtime streaming** text-to-speech over WebSocket (PCM audio chunks).
  - Auth:
    - Query param: `?api_key=<key>` (recommended for browsers)
    - Or header: `X-API-Key: <key>`
  - Client → server messages (JSON text frames):
    - `start`: `{ "type": "start", "cfg_scale"?: number, "inference_steps"?: number, "voice"?: string }`
    - `text`: `{ "type": "text", "text": string }` (buffered)
    - `flush`: `{ "type": "flush" }` (begins generation of the buffered text)
    - `stop`: `{ "type": "stop" }` (cancels current generation and clears buffer)
  - Server → client messages:
    - **Binary frames**: raw **PCM16LE mono @ 24000 Hz** audio chunks
    - JSON text frames:
      - `status`: `{ "type": "status", "event": string, "data"?: any }`
      - `error`: `{ "type": "error", "message": string }`
      - `end`: `{ "type": "end" }`
  - Notes / limitations:
    - The upstream VibeVoice realtime demo accepts the **full text at connect time**, so this API **buffers** `text` messages until you send `flush`.
    - Only one generation runs at a time per connection; additional `flush` calls during generation return an error.

- `GET /api/v1/speech/download/{filename}`
  - Returns: audio file (`audio/wav`)

### Voices

- `GET /api/v1/voices`
  - Returns: `{ voices: Voice[], total: number }`

- `POST /api/v1/voices` (multipart form)
  - Fields:
    - `name` (required)
    - `description` (optional)
    - `keywords` (optional, comma-separated)
    - `audio_files` (required, repeated: multiple files)
  - Returns: `{ success, message, voice?, validation_feedback? }`

- `POST /api/v1/voices/from-audio-clips` (multipart form)
  - Fields:
    - `name` (required)
    - `description` (optional)
    - `keywords` (optional, comma-separated)
    - `audio_file` (required, single file)
    - `clip_ranges` (required, JSON string)
      - Example: `[{"start_seconds":0.0,"end_seconds":4.2},{"start_seconds":10.0,"end_seconds":15.0}]`
  - Guardrails:
    - max clips: `50`
    - min clip duration: `0.5s`
    - max total selected duration: `600s`
  - Notes:
    - Clips are normalized to **mono, 24kHz** WAV before training.

- `PUT /api/v1/voices/{voice_id}`
  - Body (JSON): `{ name?: string, description?: string }`

- `DELETE /api/v1/voices/{voice_id}`

### Voice profiles

Voice profiles are style metadata (cadence/tone/etc.) used by Ollama-assisted features and podcast script generation.

- `POST /api/v1/voices/profile/analyze-audio` (multipart form)
  - Fields:
    - `audio_file` (required)
    - `keywords` (optional, comma-separated)
    - `ollama_url` (optional)
    - `ollama_model` (optional)
  - Returns: `{ success, message, profile?, transcript?, validation_feedback? }`
  - Notes:
    - Transcription may be unavailable on some Python versions; in that case `transcript` may be missing/null.
    - If Ollama is unreachable, this may return **HTTP 503**.

- `GET /api/v1/voices/{voice_id}/profile`
  - Returns: `{ success, message, profile? }` (profile may be `null`)

- `POST /api/v1/voices/{voice_id}/profile`
  - Create/update a profile (optionally with keywords and Ollama overrides).
  - Body (JSON): `{ keywords?: string[], ollama_url?: string, ollama_model?: string }`

- `PUT /api/v1/voices/{voice_id}/profile/keywords`
  - Update profile keywords (keywords required) and re-profile.
  - Body (JSON): `{ keywords: string[], ollama_url?: string, ollama_model?: string }`

- `POST /api/v1/voices/{voice_id}/profile/generate`
  - Force profile generation (optionally with keywords and Ollama overrides).
  - Body (JSON): `{ keywords?: string[], ollama_url?: string, ollama_model?: string }`

- `PUT /api/v1/voices/{voice_id}/profile`
  - Apply a full profile payload (works for default voices too).
  - Body (JSON): `{ cadence?, tone?, vocabulary_style?, sentence_structure?, unique_phrases?, keywords?, profile_text? }`

### Podcast generation

- `POST /api/v1/podcast/generate-script`
  - Body (JSON): `{ url, voices: string[], genre, duration, ollama_url?, ollama_model? }`
  - Returns: `{ success, message, script? }`

- `POST /api/v1/podcast/generate`
  - Body (JSON): `{ script, voices: string[], settings?, title?, source_url?, genre?, duration?, save_to_library? }`
  - Notes:
    - The backend currently **does not apply `settings` to VibeVoice inference**; generation uses VibeVoice defaults.
    - If `save_to_library` is true (default), response `audio_url` will be a library download URL.
  - Returns: `{ success, message, audio_url?, file_path?, script?, podcast_id? }`

- `GET /api/v1/podcast/download/{filename}`
  - Legacy filename-based download for items generated into the `outputs/` folder.

### Podcast library

- `GET /api/v1/podcasts?query=<optional>`
  - Returns: `{ podcasts: PodcastItem[], total }`

- `GET /api/v1/podcasts/{podcast_id}`
  - Returns JSON including metadata and (if available) `script` text.

- `GET /api/v1/podcasts/{podcast_id}/download`
  - Returns: audio file (`audio/wav`)

- `DELETE /api/v1/podcasts/{podcast_id}`
  - Deletes metadata and best-effort deletes associated audio/script files under `podcasts/`.

## Curl examples

### Generate speech

```bash
curl -sS -X POST "http://localhost:8000/api/v1/speech/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "transcript": "Speaker 1: Hello.\nSpeaker 2: Hi there.",
    "speakers": ["Alice", "Frank"]
  }'
```

### Create voice (multi-file upload)

```bash
curl -sS -X POST "http://localhost:8000/api/v1/voices" \
  -H "X-API-Key: ${API_KEY}" \
  -F 'name=MyVoice' \
  -F 'description=Demo voice' \
  -F 'keywords=podcast,tech' \
  -F 'audio_files=@/path/to/clip1.wav' \
  -F 'audio_files=@/path/to/clip2.wav'
```

### Create voice from clips (single file + ranges)

```bash
curl -sS -X POST "http://localhost:8000/api/v1/voices/from-audio-clips" \
  -H "X-API-Key: ${API_KEY}" \
  -F 'name=MyClippedVoice' \
  -F 'audio_file=@/path/to/long_recording.mp3' \
  -F 'clip_ranges=[{"start_seconds":0.0,"end_seconds":5.0},{"start_seconds":12.0,"end_seconds":18.0}]'
```

### Analyze audio → apply profile to a voice

```bash
curl -sS -X POST "http://localhost:8000/api/v1/voices/profile/analyze-audio" \
  -H "X-API-Key: ${API_KEY}" \
  -F 'audio_file=@/path/to/sample.wav' \
  -F 'keywords=finance,markets'
```

Then apply the returned profile payload:

```bash
curl -sS -X PUT "http://localhost:8000/api/v1/voices/<voice_id>/profile" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "tone": "calm and confident",
    "cadence": "medium pace, clear pauses",
    "keywords": ["finance", "markets"]
  }'
```

### Generate podcast script → audio (saved to library) → download

```bash
curl -sS -X POST "http://localhost:8000/api/v1/podcast/generate-script" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "url": "https://example.com/article",
    "voices": ["Alice", "Frank"],
    "genre": "News",
    "duration": "10 min"
  }'
```

```bash
curl -sS -X POST "http://localhost:8000/api/v1/podcast/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "script": "Speaker 1: Welcome...\nSpeaker 2: Today we discuss...",
    "voices": ["Alice", "Frank"],
    "title": "My Podcast",
    "save_to_library": true
  }'
```

If the response includes `podcast_id`, download via:

```bash
curl -L "http://localhost:8000/api/v1/podcasts/<podcast_id>/download" \
  -H "X-API-Key: ${API_KEY}" \
  --output podcast.wav
```

