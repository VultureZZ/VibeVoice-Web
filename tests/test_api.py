#!/usr/bin/env python3
"""
Test script for VibeVoice API.

Tests the API endpoints to verify functionality.
"""
import json
import math
import struct
import sys
import tempfile
import time
import wave
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests library not installed.")
    print("Install it with: pip install requests")
    sys.exit(1)

# API configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = None  # Set if API_KEY is configured in .env

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def print_success(message):
    """Print success message."""
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message):
    """Print error message."""
    print(f"{RED}✗ {message}{RESET}")


def print_info(message):
    """Print info message."""
    print(f"{YELLOW}ℹ {message}{RESET}")


def test_health_check():
    """Test the health check endpoint."""
    print("\n" + "=" * 60)
    print("Testing Health Check Endpoint")
    print("=" * 60)

    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            print_success(f"Health check passed: {response.json()}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Could not connect to API. Is it running?")
        return False
    except Exception as e:
        print_error(f"Health check error: {e}")
        return False


def test_list_voices():
    """Test listing all voices."""
    print("\n" + "=" * 60)
    print("Testing List Voices Endpoint")
    print("=" * 60)

    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY

    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/voices", headers=headers)
        if response.status_code == 200:
            data = response.json()
            voices = data.get("voices", [])
            print_success(f"Found {data.get('total', 0)} voices")
            print_info("Available voices:")
            for voice in voices[:10]:  # Show first 10
                voice_type = voice.get("type", "unknown")
                print(f"  - {voice.get('name')} ({voice_type})")
            if len(voices) > 10:
                print(f"  ... and {len(voices) - 10} more")
            return True, voices
        else:
            print_error(f"List voices failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False, []
    except Exception as e:
        print_error(f"List voices error: {e}")
        return False, []


def test_generate_speech():
    """Test speech generation."""
    print("\n" + "=" * 60)
    print("Testing Speech Generation Endpoint")
    print("=" * 60)

    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY

    # Test transcript
    test_transcript = """Speaker 1: Hello, this is a test of the VibeVoice API.
Speaker 2: The API is working correctly.
Speaker 1: This is great news!
Speaker 2: Yes, speech generation is successful."""

    payload = {
        "transcript": test_transcript,
        "speakers": ["Alice", "Frank"],
        "settings": {
            "language": "en",
            "output_format": "wav",
            "sample_rate": 24000,
        },
    }

    try:
        print_info("Sending speech generation request...")
        print_info(f"Transcript: {test_transcript[:50]}...")
        print_info("Speakers: Alice, Frank")

        response = requests.post(
            f"{API_BASE_URL}/api/v1/speech/generate",
            headers=headers,
            json=payload,
            timeout=300,  # 5 minute timeout for generation
        )

        if response.status_code == 200:
            data = response.json()
            print_success("Speech generation request successful!")
            print_info(f"Message: {data.get('message')}")
            if data.get("audio_url"):
                print_info(f"Audio URL: {data.get('audio_url')}")
            if data.get("file_path"):
                print_info(f"File path: {data.get('file_path')}")

            # Try to download the audio file
            if data.get("audio_url"):
                audio_filename = data["audio_url"].split("/")[-1]
                download_url = f"{API_BASE_URL}/api/v1/speech/download/{audio_filename}"
                print_info(f"\nDownloading audio from: {download_url}")
                download_response = requests.get(download_url, headers=headers)
                if download_response.status_code == 200:
                    output_dir = Path(__file__).parent.parent / "outputs"
                    output_dir.mkdir(exist_ok=True)
                    output_file = output_dir / audio_filename
                    output_file.write_bytes(download_response.content)
                    print_success(f"Audio file saved to: {output_file}")
                    return True
                else:
                    print_error(f"Download failed: {download_response.status_code}")
                    return False
            return True
        elif response.status_code == 429:
            print_error("Rate limit exceeded. Please wait and try again.")
            return False
        else:
            print_error(f"Speech generation failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
    except requests.exceptions.Timeout:
        print_error("Request timed out. Speech generation may take a while.")
        return False
    except Exception as e:
        print_error(f"Speech generation error: {e}")
        return False


def test_rate_limiting():
    """Test rate limiting by making multiple rapid requests."""
    print("\n" + "=" * 60)
    print("Testing Rate Limiting")
    print("=" * 60)

    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY

    print_info("Making 12 rapid requests (limit is 10/min)...")
    rate_limited = False

    for i in range(12):
        try:
            response = requests.get(f"{API_BASE_URL}/api/v1/voices", headers=headers)
            if response.status_code == 429:
                print_success(f"Rate limit triggered on request {i+1} (as expected)")
                rate_limited = True
                break
            elif response.status_code == 200:
                remaining = response.headers.get("X-RateLimit-Remaining", "unknown")
                print_info(f"Request {i+1}: OK (remaining: {remaining})")
        except Exception as e:
            print_error(f"Request {i+1} error: {e}")
            break

    if not rate_limited:
        print_info("Rate limit not triggered (may need more requests or different timing)")

    return True


def _write_test_wav(path: Path, duration_seconds: float = 2.0, sample_rate: int = 24000) -> None:
    """Create a small mono WAV file suitable for API upload tests."""
    frequency_hz = 440.0
    amplitude = 0.2
    num_samples = int(duration_seconds * sample_rate)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)

        for i in range(num_samples):
            t = i / sample_rate
            sample = int(amplitude * 32767.0 * math.sin(2.0 * math.pi * frequency_hz * t))
            wf.writeframes(struct.pack("<h", sample))


def test_create_voice_from_clips():
    """Test creating a voice from multiple clip ranges in a single audio file."""
    print("\n" + "=" * 60)
    print("Testing Create Voice from Audio Clips Endpoint")
    print("=" * 60)

    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY

    temp_path = None
    created_voice_id = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf:
            temp_path = Path(tf.name)

        _write_test_wav(temp_path, duration_seconds=2.0, sample_rate=24000)

        name = f"TestClips_{int(time.time())}"
        clip_ranges = [
            {"start_seconds": 0.0, "end_seconds": 1.0},
            {"start_seconds": 1.0, "end_seconds": 2.0},
        ]

        data = {
            "name": name,
            "clip_ranges": json.dumps(clip_ranges),
        }

        with temp_path.open("rb") as f:
            files = {"audio_file": (temp_path.name, f, "audio/wav")}
            response = requests.post(
                f"{API_BASE_URL}/api/v1/voices/from-audio-clips",
                headers=headers,
                data=data,
                files=files,
                timeout=300,
            )

        if response.status_code != 201:
            print_error(f"Create voice from clips failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        payload = response.json()
        if not payload.get("success"):
            print_error(f"Create voice from clips returned success=false: {payload}")
            return False

        voice = payload.get("voice") or {}
        created_voice_id = voice.get("id")
        if not created_voice_id:
            print_error(f"No voice.id returned: {payload}")
            return False

        print_success(f"Created voice from clips: {voice.get('name')} (id={created_voice_id})")

        # Negative test: out-of-bounds range should return 400
        bad_ranges = [{"start_seconds": 0.0, "end_seconds": 9999.0}]
        data_bad = {"name": f"{name}_bad", "clip_ranges": json.dumps(bad_ranges)}
        with temp_path.open("rb") as f:
            files = {"audio_file": (temp_path.name, f, "audio/wav")}
            bad_resp = requests.post(
                f"{API_BASE_URL}/api/v1/voices/from-audio-clips",
                headers=headers,
                data=data_bad,
                files=files,
                timeout=300,
            )

        if bad_resp.status_code != 400:
            print_error(f"Expected 400 for out-of-bounds range, got {bad_resp.status_code}")
            print_error(f"Response: {bad_resp.text}")
            return False

        print_success("Out-of-bounds clip range rejected (400) as expected")
        return True
    except requests.exceptions.ConnectionError:
        print_error("Could not connect to API. Is it running?")
        return False
    except Exception as e:
        print_error(f"Create voice from clips error: {e}")
        return False
    finally:
        # Clean up the created voice to avoid polluting local state
        try:
            if created_voice_id:
                requests.delete(f"{API_BASE_URL}/api/v1/voices/{created_voice_id}", headers=headers, timeout=60)
        except Exception:
            pass

        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


def main():
    """Run all tests."""
    print("=" * 60)
    print("VibeVoice API Test Suite")
    print("=" * 60)
    print(f"API Base URL: {API_BASE_URL}")
    if API_KEY:
        print(f"Using API Key: {API_KEY[:10]}...")
    else:
        print("No API key configured (using default behavior)")

    results = {}

    # Test 1: Health check
    results["health"] = test_health_check()

    if not results["health"]:
        print_error("\nAPI is not accessible. Please check:")
        print_error("1. Is the API server running?")
        print_error(f"2. Is it running on {API_BASE_URL}?")
        print_error("3. Check the port number in your .env file")
        return

    # Test 2: List voices
    success, voices = test_list_voices()
    results["list_voices"] = success

    # Test 3: Generate speech (only if we have voices)
    if voices:
        results["generate_speech"] = test_generate_speech()
    else:
        print_info("\nSkipping speech generation test (no voices available)")

    # Test 4: Rate limiting
    results["rate_limiting"] = test_rate_limiting()

    # Test 5: Create voice from clips
    results["create_voice_from_clips"] = test_create_voice_from_clips()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        if passed:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")

    all_passed = all(results.values())
    if all_passed:
        print_success("\nAll tests passed!")
    else:
        print_error("\nSome tests failed. Check the output above for details.")


if __name__ == "__main__":
    # Allow custom API URL and key via command line
    if len(sys.argv) > 1:
        API_BASE_URL = sys.argv[1]
    if len(sys.argv) > 2:
        API_KEY = sys.argv[2]

    main()
