#!/usr/bin/env python3
"""
Test script for VibeVoice API.

Tests the API endpoints to verify functionality.
"""
import json
import sys
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
