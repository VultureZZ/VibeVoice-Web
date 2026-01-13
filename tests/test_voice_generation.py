#!/usr/bin/env python3
"""
Test script for VibeVoice voice generation.

This script generates voice from a sample transcript using the VibeVoice model.
Based on the beginner's guide: https://www.kdnuggets.com/beginners-guide-to-vibevoice
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configuration
VIBEVOICE_REPO_DIR = project_root / "VibeVoice"
MODEL_DIR = project_root / "models" / "VibeVoice-1.5B"
OUTPUT_DIR = project_root / "outputs"
SAMPLE_TRANSCRIPT = project_root / "tests" / "sample_transcript.txt"

# Default speaker names (can be overridden)
DEFAULT_SPEAKERS = ["Alice", "Frank"]


def check_dependencies():
    """Check if required dependencies are available."""
    print("Checking dependencies...")
    
    # Check if VibeVoice repo exists
    if not VIBEVOICE_REPO_DIR.exists():
        print(f"✗ VibeVoice repository not found at {VIBEVOICE_REPO_DIR}")
        print("  Run: python scripts/setup_vibevoice.py")
        return False
    print(f"✓ VibeVoice repository found")
    
    # Check if model exists
    if not MODEL_DIR.exists() or not any(MODEL_DIR.iterdir()):
        print(f"✗ Model not found at {MODEL_DIR}")
        print("  Run: python scripts/setup_vibevoice.py")
        return False
    print(f"✓ Model found")
    
    # Check if inference script exists
    inference_script = VIBEVOICE_REPO_DIR / "demo" / "inference_from_file.py"
    if not inference_script.exists():
        print(f"✗ Inference script not found at {inference_script}")
        return False
    print(f"✓ Inference script found")
    
    # Check for CUDA
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✓ CUDA available (device: {torch.cuda.get_device_name(0)})")
        else:
            print("⚠ CUDA not available - will use CPU (slower)")
    except ImportError:
        print("⚠ PyTorch not installed")
    
    return True


def create_sample_transcript():
    """Create a sample transcript file for testing."""
    transcript_content = """Speaker 1: Have you heard about VibeVoice?
Speaker 2: Yes, it's Microsoft's open-source text-to-speech model.
Speaker 1: I'm excited to test it out. It can generate natural, expressive speech.
Speaker 2: Absolutely, and it supports multiple speakers in conversations.
Speaker 1: That's perfect for creating podcast-style content.
Speaker 2: Let's generate some audio and see how it sounds!
"""
    
    SAMPLE_TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE_TRANSCRIPT.write_text(transcript_content)
    print(f"✓ Created sample transcript at {SAMPLE_TRANSCRIPT}")
    return SAMPLE_TRANSCRIPT


def run_inference(transcript_path, speaker_names):
    """Run VibeVoice inference on the transcript."""
    inference_script = VIBEVOICE_REPO_DIR / "demo" / "inference_from_file.py"
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Build command
    cmd = [
        sys.executable,
        str(inference_script),
        "--model_path", str(MODEL_DIR),
        "--txt_path", str(transcript_path),
        "--speaker_names"
    ] + speaker_names
    
    print("\n" + "=" * 60)
    print("Running VibeVoice inference...")
    print("=" * 60)
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        # Run inference
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            check=True,
            capture_output=False  # Show output in real-time
        )
        
        print("\n" + "=" * 60)
        print("Inference completed successfully!")
        print("=" * 60)
        
        # Try to find the output file
        output_files = list(OUTPUT_DIR.glob("*generated.wav"))
        if output_files:
            output_file = output_files[-1]  # Get most recent
            print(f"\nOutput audio file: {output_file}")
            print(f"File size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
            return output_file
        else:
            print("\n⚠ Output file not found in expected location")
            print(f"  Check the outputs directory: {OUTPUT_DIR}")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Inference failed with exit code {e.returncode}", file=sys.stderr)
        return None
    except KeyboardInterrupt:
        print("\n\n⚠ Inference interrupted by user")
        return None


def main():
    """Main test function."""
    print("=" * 60)
    print("VibeVoice Voice Generation Test")
    print("=" * 60)
    print()
    
    # Check dependencies
    if not check_dependencies():
        print("\n✗ Dependency check failed. Please run setup first.")
        sys.exit(1)
    
    # Create sample transcript
    print("\nCreating sample transcript...")
    transcript_path = create_sample_transcript()
    
    # Get speaker names from command line or use defaults
    if len(sys.argv) > 1:
        speaker_names = sys.argv[1:]
    else:
        speaker_names = DEFAULT_SPEAKERS
    
    print(f"\nUsing speakers: {', '.join(speaker_names)}")
    
    # Run inference
    output_file = run_inference(transcript_path, speaker_names)
    
    if output_file:
        print("\n" + "=" * 60)
        print("Test completed successfully!")
        print("=" * 60)
        print(f"\nGenerated audio: {output_file}")
        print("\nTo play the audio:")
        print(f"  - On macOS: open {output_file}")
        print(f"  - On Linux: xdg-open {output_file}")
        print(f"  - Or use any audio player")
    else:
        print("\n" + "=" * 60)
        print("Test completed with errors")
        print("=" * 60)
        print("\nTroubleshooting:")
        print("1. Check that the model is fully downloaded")
        print("2. Verify CUDA is available (or use CPU)")
        print("3. Check the error messages above")
        sys.exit(1)


if __name__ == "__main__":
    main()
