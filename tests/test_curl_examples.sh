#!/bin/bash
# Example curl commands for testing the AudioMesh API

API_URL="http://localhost:8000"

echo "=== AudioMesh API Test Commands ==="
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
curl -X POST "$API_URL/api/v1/speech/generate" \
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
curl -X POST "$API_URL/api/v1/speech/generate" \
  -H "Content-Type: application/json" \
  -d @request.json
EOF
echo ""

# Generate speech - Multi-line with proper escaping
echo "5. Generate Speech (multi-line with proper escaping):"
cat << 'EOF'
curl -X POST "$API_URL/api/v1/speech/generate" \
  -H "Content-Type: application/json" \
  -d $'{"transcript": "Speaker 1: Hello world\\nSpeaker 2: This is a test", "speakers": ["Alice", "Frank"]}'
EOF
echo ""

# Create custom voice - Single file
echo "6. Create Custom Voice (single audio file):"
cat << 'EOF'
curl -X POST "$API_URL/api/v1/voices" \
  -H "X-API-Key: your-api-key-here" \
  -F "name=MyCustomVoice" \
  -F "description=A custom voice trained from my audio files" \
  -F "audio_files=@/path/to/your/audio1.wav"
EOF
echo ""

# Create custom voice - Multiple files
echo "7. Create Custom Voice (multiple audio files):"
cat << 'EOF'
curl -X POST "$API_URL/api/v1/voices" \
  -H "X-API-Key: your-api-key-here" \
  -F "name=MyCustomVoice" \
  -F "description=A custom voice trained from multiple audio files" \
  -F "audio_files=@/path/to/your/audio1.wav" \
  -F "audio_files=@/path/to/your/audio2.wav" \
  -F "audio_files=@/path/to/your/audio3.wav"
EOF
echo ""

# Create custom voice - Without API key (if API key not required)
echo "8. Create Custom Voice (without API key):"
cat << 'EOF'
curl -X POST "$API_URL/api/v1/voices" \
  -F "name=MyCustomVoice" \
  -F "description=Custom voice without API key" \
  -F "audio_files=@/path/to/your/audio.wav"
EOF
echo ""

# Create custom voice - With validation feedback
echo "9. Create Custom Voice (with validation feedback in response):"
cat << 'EOF'
# The response will include validation_feedback with:
# - total_duration_seconds
# - individual_files analysis
# - warnings (if any)
# - recommendations
# - quality_metrics

curl -X POST "$API_URL/api/v1/voices" \
  -H "X-API-Key: your-api-key-here" \
  -F "name=MyCustomVoice" \
  -F "description=Voice with validation feedback" \
  -F "audio_files=@/path/to/your/audio1.wav" \
  -F "audio_files=@/path/to/your/audio2.wav" \
  | jq '.'
EOF
echo ""
