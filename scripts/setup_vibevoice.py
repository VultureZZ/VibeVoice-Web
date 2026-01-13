#!/usr/bin/env python3
"""
Setup script for VibeVoice project.

This script:
1. Clones the community VibeVoice repository
2. Downloads the VibeVoice-1.5B model from Hugging Face
3. Installs the VibeVoice package
4. Verifies the installation
"""

import os
import sys
import subprocess
from pathlib import Path
from huggingface_hub import snapshot_download

# Configuration
VIBEVOICE_REPO_URL = "https://github.com/vibevoice-community/VibeVoice.git"
VIBEVOICE_REPO_DIR = Path(__file__).parent.parent / "VibeVoice"
MODEL_REPO_ID = "microsoft/VibeVoice-1.5B"
MODEL_DIR = Path(__file__).parent.parent / "models" / "VibeVoice-1.5B"


def run_command(cmd, cwd=None, check=True):
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(
        cmd,
        shell=isinstance(cmd, str),
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr and result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
    return result


def clone_vibevoice_repo():
    """Clone the VibeVoice community repository."""
    if VIBEVOICE_REPO_DIR.exists():
        print(f"VibeVoice repository already exists at {VIBEVOICE_REPO_DIR}")
        print("Skipping clone. To re-clone, delete the directory first.")
        return True
    
    print(f"Cloning VibeVoice repository to {VIBEVOICE_REPO_DIR}...")
    try:
        run_command(
            ["git", "clone", "--depth", "1", VIBEVOICE_REPO_URL, str(VIBEVOICE_REPO_DIR)]
        )
        print("✓ Repository cloned successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to clone repository: {e}", file=sys.stderr)
        return False


def install_vibevoice_package():
    """Install the VibeVoice package in editable mode."""
    if not VIBEVOICE_REPO_DIR.exists():
        print("✗ VibeVoice repository not found. Run clone first.", file=sys.stderr)
        return False
    
    print("Installing VibeVoice package...")
    try:
        run_command(
            ["pip", "install", "-e", str(VIBEVOICE_REPO_DIR)]
        )
        print("✓ VibeVoice package installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install package: {e}", file=sys.stderr)
        return False


def download_model():
    """Download the VibeVoice-1.5B model from Hugging Face."""
    if MODEL_DIR.exists() and any(MODEL_DIR.iterdir()):
        print(f"Model already exists at {MODEL_DIR}")
        print("Skipping download. To re-download, delete the directory first.")
        return True
    
    print(f"Downloading model {MODEL_REPO_ID} to {MODEL_DIR}...")
    print("This may take a while (model is ~5.4 GB)...")
    
    try:
        MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=MODEL_REPO_ID,
            local_dir=str(MODEL_DIR),
            local_dir_use_symlinks=False
        )
        print("✓ Model downloaded successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to download model: {e}", file=sys.stderr)
        return False


def verify_installation():
    """Verify that the installation is complete."""
    print("\nVerifying installation...")
    
    checks = {
        "VibeVoice repository": VIBEVOICE_REPO_DIR.exists(),
        "Model directory": MODEL_DIR.exists() and any(MODEL_DIR.iterdir()),
    }
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False
    
    # Try to import vibevoice to verify package installation
    try:
        import vibevoice
        print("✓ VibeVoice package importable")
    except ImportError:
        print("✗ VibeVoice package not importable (may need to install)")
        all_passed = False
    
    return all_passed


def main():
    """Main setup function."""
    print("=" * 60)
    print("VibeVoice Setup Script")
    print("=" * 60)
    print()
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    success = True
    
    # Step 1: Clone repository
    print("\n[1/4] Cloning VibeVoice repository...")
    if not clone_vibevoice_repo():
        success = False
    
    # Step 2: Install package
    print("\n[2/4] Installing VibeVoice package...")
    if not install_vibevoice_package():
        success = False
    
    # Step 3: Download model
    print("\n[3/4] Downloading model from Hugging Face...")
    if not download_model():
        success = False
    
    # Step 4: Verify installation
    print("\n[4/4] Verifying installation...")
    if not verify_installation():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("Setup completed successfully!")
        print("\nNext steps:")
        print("1. Run the test script: python tests/test_voice_generation.py")
        print("2. Check the outputs/ directory for generated audio files")
    else:
        print("Setup completed with errors. Please review the messages above.")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
