#!/usr/bin/env python3
"""
Test script for voice generation.

Uses the application voice_generator with the configured TTS backend
(TTS_BACKEND=qwen3 for Qwen3-TTS, or TTS_BACKEND=vibevoice for legacy VibeVoice).
"""

import os
import sys
from pathlib import Path

# Add src to path (same as run_api.py)
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

OUTPUT_DIR = project_root / "outputs"
SAMPLE_TRANSCRIPT_PATH = project_root / "tests" / "sample_transcript.txt"
DEFAULT_SPEAKERS = ["Alice", "Frank"]


def check_dependencies():
    """Check if required dependencies are available for the configured backend."""
    backend = (os.getenv("TTS_BACKEND") or "qwen3").strip().lower()
    print("Checking dependencies (TTS_BACKEND=%s)..." % backend)

    if backend == "vibevoice":
        vibevoice_repo = project_root / os.getenv("VIBEVOICE_REPO_DIR", "VibeVoice")
        model_dir = project_root / os.getenv("MODEL_PATH", "models/VibeVoice-1.5B")
        if not vibevoice_repo.exists():
            print("  VibeVoice repository not found at %s" % vibevoice_repo)
            print("  Run setup or set TTS_BACKEND=qwen3 to use Qwen3-TTS")
            return False
        if not model_dir.exists() or not any(model_dir.iterdir()):
            print("  Model not found at %s" % model_dir)
            return False
        inference_script = vibevoice_repo / "demo" / "inference_from_file.py"
        if not inference_script.exists():
            print("  Inference script not found at %s" % inference_script)
            return False
        print("  VibeVoice repo and model found")
    else:
        try:
            import qwen_tts  # noqa: F401
            print("  qwen-tts package found")
        except ImportError:
            print("  qwen-tts not installed. Run: pip install qwen-tts")
            print("  Or set TTS_BACKEND=vibevoice to use legacy VibeVoice")
            return False

    try:
        import torch
        if torch.cuda.is_available():
            print("  CUDA available: %s" % torch.cuda.get_device_name(0))
        else:
            print("  CUDA not available (will use CPU)")
    except ImportError:
        print("  PyTorch not installed")
    return True


def create_sample_transcript():
    """Create a sample transcript file for testing."""
    content = """Speaker 1: Have you heard about VibeVoice?
Speaker 2: Yes, it's Microsoft's open-source text-to-speech model.
Speaker 1: I'm excited to test it out. It can generate natural, expressive speech.
Speaker 2: Absolutely, and it supports multiple speakers in conversations.
Speaker 1: That's perfect for creating podcast-style content.
Speaker 2: Let's generate some audio and see how it sounds!
"""
    SAMPLE_TRANSCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE_TRANSCRIPT_PATH.write_text(content)
    print("Created sample transcript at %s" % SAMPLE_TRANSCRIPT_PATH)
    return content


def main():
    """Run voice generation using the application voice_generator."""
    print("=" * 60)
    print("Voice Generation Test")
    print("=" * 60)

    if not check_dependencies():
        print("\nDependency check failed.")
        sys.exit(1)

    transcript = create_sample_transcript()
    speakers = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_SPEAKERS
    print("\nUsing speakers: %s" % ", ".join(speakers))

    # Use application voice_generator (respects TTS_BACKEND env)
    from vibevoice.services.voice_generator import voice_generator

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("\nRunning voice generation...")
    try:
        output_path = voice_generator.generate_speech(
            transcript=transcript,
            speakers=speakers,
            language="en",
        )
        print("\nGeneration completed successfully")
        print("Output: %s" % output_path)
        print("File size: %.2f MB" % (output_path.stat().st_size / (1024 * 1024)))
        return
    except Exception as e:
        print("\nGeneration failed: %s" % e)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
