#!/usr/bin/env python3
"""
Setup script for AudioMesh model dependencies.

This script:
1. Clones the community VibeVoice repository (legacy backend support)
2. Downloads the VibeVoice-1.5B model from Hugging Face
3. Installs the VibeVoice package
4. Clones ACE-Step-1.5 for music generation
5. Runs `uv sync` in ACE-Step-1.5 to install its dependencies
6. Verifies the installation
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from huggingface_hub import snapshot_download

# Configuration
VIBEVOICE_REPO_URL = "https://github.com/vibevoice-community/VibeVoice.git"
VIBEVOICE_REPO_DIR = Path(__file__).parent.parent / "VibeVoice"
MODEL_REPO_ID = "microsoft/VibeVoice-1.5B"
MODEL_DIR = Path(__file__).parent.parent / "models" / "VibeVoice-1.5B"
ACESTEP_REPO_URL = "https://github.com/ace-step/ACE-Step-1.5.git"
ACESTEP_REPO_DIR = Path(__file__).parent.parent / "ACE-Step-1.5"


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


def clone_ace_step_repo():
    """Clone ACE-Step repository used by AudioMesh music generation."""
    if ACESTEP_REPO_DIR.exists():
        print(f"ACE-Step repository already exists at {ACESTEP_REPO_DIR}")
        print("Skipping clone. To re-clone, delete the directory first.")
        return True

    print(f"Cloning ACE-Step repository to {ACESTEP_REPO_DIR}...")
    try:
        run_command(
            ["git", "clone", "--depth", "1", ACESTEP_REPO_URL, str(ACESTEP_REPO_DIR)]
        )
        print("✓ ACE-Step repository cloned successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to clone ACE-Step repository: {e}", file=sys.stderr)
        return False


def install_ace_step_dependencies():
    """
    Install ACE-Step dependencies with uv sync.

    We intentionally use uv to match ACE-Step's recommended setup flow.
    """
    if not ACESTEP_REPO_DIR.exists():
        print("✗ ACE-Step repository not found. Run clone first.", file=sys.stderr)
        return False

    uv_binary = shutil.which("uv")
    if not uv_binary:
        print(
            "✗ `uv` was not found in PATH. Install it first: https://astral.sh/uv/install.sh",
            file=sys.stderr,
        )
        return False

    print("Installing ACE-Step dependencies with uv sync...")
    try:
        run_command([uv_binary, "sync"], cwd=str(ACESTEP_REPO_DIR))
        print("✓ ACE-Step dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install ACE-Step dependencies: {e}", file=sys.stderr)
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
        "ACE-Step repository": ACESTEP_REPO_DIR.exists(),
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
    
    # Step 4: Clone ACE-Step repository
    print("\n[4/6] Cloning ACE-Step repository...")
    if not clone_ace_step_repo():
        success = False

    # Step 5: Install ACE-Step dependencies
    print("\n[5/6] Installing ACE-Step dependencies...")
    if not install_ace_step_dependencies():
        success = False

    # Step 6: Verify installation
    print("\n[6/6] Verifying installation...")
    if not verify_installation():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("Setup completed successfully!")
        print("\nNext steps:")
        print("1. Run the API: python run_api.py")
        print("2. Open the Music page in the WebUI and generate your first track")
        print("3. Check the outputs/ directory for generated files")
    else:
        print("Setup completed with errors. Please review the messages above.")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
