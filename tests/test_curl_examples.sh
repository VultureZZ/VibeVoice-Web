#!/bin/bash
# Example curl commands for testing the VibeVoice API

API_URL="http://localhost:8008"
# Or use: API_URL="http://server-ai.mrhelpmann.com:8008"

echo "=== VibeVoice API Test Commands ==="
echo ""

# Health check
echo "1. Health Check:"
echo "curl $API_URL/health"
echo ""

# List voices
echo "2. List Voices:"
echo "curl $API_URL/api/v1/voices"
echo ""

# Generate speech - Single line version (recommended)
echo "3. Generate Speech (single line):"
cat << 'EOF'
curl -X POST http://localhost:8008/api/v1/speech/generate \
  -H "Content-Type: application/json" \
  -d '{"transcript": "Speaker 1: Hello world\nSpeaker 2: This is a test", "speakers": ["Alice", "Frank"]}'
EOF
echo ""

# Generate speech - Using a file (best for complex transcripts)
echo "4. Generate Speech (using JSON file):"
cat << 'EOF'
# Create request.json:
cat > request.json << 'JSON'
{
  "transcript": "Speaker 1: Hello world\nSpeaker 2: This is a test",
  "speakers": ["Alice", "Frank"],
  "settings": {
    "language": "en",
    "output_format": "wav",
    "sample_rate": 24000
  }
}
JSON

# Then run:
curl -X POST http://localhost:8008/api/v1/speech/generate \
  -H "Content-Type: application/json" \
  -d @request.json
EOF
echo ""

# Generate speech - Multi-line with proper escaping
echo "5. Generate Speech (multi-line with proper escaping):"
cat << 'EOF'
curl -X POST http://localhost:8008/api/v1/speech/generate \
  -H "Content-Type: application/json" \
  -d $'{"transcript": "Speaker 1: Hello world\\nSpeaker 2: This is a test", "speakers": ["Alice", "Frank"]}'
EOF
echo ""
