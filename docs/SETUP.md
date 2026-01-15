# Detailed Setup Guide

This guide provides step-by-step instructions for setting up the VibeVoice project from scratch.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Manual Setup (Alternative)](#manual-setup-alternative)
4. [Verification](#verification)
5. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python**: 3.8 or higher
- **RAM**: Minimum 8GB (16GB recommended)
- **Disk Space**: ~6GB for the model
- **GPU**: CUDA-capable GPU recommended (NVIDIA with CUDA 11.8+)

### Software Requirements

1. **Python 3.8+**
   ```bash
   python --version
   ```

2. **ffmpeg** (required for audio decoding via `pydub`, and recommended for audio profiling/transcription)
   - macOS (Homebrew):
   ```bash
   brew install ffmpeg
   ```
   - Linux:
   ```bash
   # Example (Debian/Ubuntu)
   sudo apt-get update && sudo apt-get install -y ffmpeg
   ```

2. **Git**
   ```bash
   git --version
   ```

3. **pip** (usually comes with Python)
   ```bash
   pip --version
   ```

4. **CUDA Toolkit** (for GPU support)
   - Check if CUDA is available: `nvidia-smi`
   - Install from [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-downloads)

5. **Ollama** (recommended for podcast scripting and voice profiling)
   - Install and run Ollama, then ensure it’s reachable at the configured URL (default `http://localhost:11434`).
   - Pull a model (default `llama3.2`): `ollama pull llama3.2`

## Initial Setup

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd VibeVoice-Web
```

### Step 2: Create Virtual Environment

**On Linux/macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**On Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

### Step 3: Install Base Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Notes:
- On Python 3.13+, `audioop` is removed from stdlib. This project installs `audioop-lts` automatically for `pydub` compatibility.
- Audio transcription for “Voice Profile from Audio” requires `faster-whisper`, which is installed automatically on Python < 3.13. On newer Python versions, transcription is disabled and the API will return a minimal profile.

### Step 4: Run Automated Setup

The setup script will handle:
- Cloning the VibeVoice community repository
- Installing the VibeVoice package
- Downloading the VibeVoice-1.5B model from Hugging Face

```bash
python scripts/setup_vibevoice.py
```

**Expected output:**
```
============================================================
VibeVoice Setup Script
============================================================

[1/4] Cloning VibeVoice repository...
Cloning VibeVoice repository to /path/to/VibeVoice-Web/VibeVoice...
✓ Repository cloned successfully

[2/4] Installing VibeVoice package...
Installing VibeVoice package...
✓ VibeVoice package installed successfully

[3/4] Downloading model from Hugging Face...
Downloading model microsoft/VibeVoice-1.5B to /path/to/models/VibeVoice-1.5B...
This may take a while (model is ~5.4 GB)...
✓ Model downloaded successfully

[4/4] Verifying installation...
✓ VibeVoice repository
✓ Model directory
✓ VibeVoice package importable

Setup completed successfully!
```

### Step 5: Verify Installation

Run the test script to verify everything works:

```bash
python tests/test_voice_generation.py
```

You should see output indicating successful voice generation, and an audio file in the `outputs/` directory.

## Manual Setup (Alternative)

If the automated setup script fails, you can set up manually:

### 1. Clone VibeVoice Repository

```bash
git clone --depth 1 https://github.com/vibevoice-community/VibeVoice.git
```

### 2. Install VibeVoice Package

```bash
pip install -e VibeVoice/
```

### 3. Download Model

```python
from huggingface_hub import snapshot_download

snapshot_download(
    "microsoft/VibeVoice-1.5B",
    local_dir="models/VibeVoice-1.5B",
    local_dir_use_symlinks=False
)
```

Or using the command line:

```bash
huggingface-cli download microsoft/VibeVoice-1.5B --local-dir models/VibeVoice-1.5B
```

## Verification

### Check GPU Availability

```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
```

### Verify Model Files

Check that the model directory contains the necessary files:

```bash
ls -lh models/VibeVoice-1.5B/
```

You should see files like:
- `config.json`
- `model.safetensors.index.json`
- `model-00001-of-00003.safetensors`
- `model-00002-of-00003.safetensors`
- `model-00003-of-00003.safetensors`
- `preprocessor_config.json`

### Test Import

```python
import vibevoice
print("VibeVoice imported successfully")
```

## API Reference

- **Interactive API docs**: `http://localhost:8000/docs`
- **Full endpoint reference**: [`docs/API.md`](API.md)

## Features: Podcast Library + Voice Profile from Audio

### Podcast Library
- Generated podcasts can be saved to the on-disk library under `podcasts/` (metadata JSON + audio + script).
- The frontend “Podcast Library” page lists/searches/deletes saved items.

### Voice Profile from Audio
- In the UI, go to **Voices → Analyze Audio → Profile**.
- Upload an audio file, the backend will:
  - validate audio (duration/quality warnings)
  - attempt transcription (if supported by your Python version)
  - generate a style-oriented profile (cadence/tone/vocabulary) via Ollama
  - allow you to apply/copy the profile onto any voice

### Create Voice from Clips (single file → multiple ranges)
- In the UI, go to **Voices → Create from Clips**.
- Upload one audio file, then select multiple time ranges (clips).
- Recommended clip selection:
  - multiple clips of **3–10 seconds** each
  - keep the total selected duration under a few minutes for best results
- API endpoint used by the UI:
  - `POST /api/v1/voices/from-audio-clips` (multipart form)
  - fields:
    - `name` (required)
    - `description` (optional)
    - `keywords` (optional, comma-separated)
    - `audio_file` (required)
    - `clip_ranges` (required JSON array like `[{"start_seconds": 0.0, "end_seconds": 4.2}, ...]`)

## Troubleshooting

### Issue: FlashAttention2 Warning

**Symptoms:**
- Warning: "FlashAttention2 has been toggled on, but it cannot be used due to the following error: the package flash_attn seems to be not installed"
- Model falls back to SDPA (scaled dot product attention)

**Note:** This is not an error! The model will work fine with SDPA. FlashAttention2 is optional and provides faster inference, but SDPA is a good fallback.

**Solutions (Optional - for faster inference):**
1. Install FlashAttention2 (requires matching CUDA/PyTorch versions):
   ```bash
   pip install flash-attn --no-build-isolation
   ```
2. Verify installation: `python -c "import flash_attn; print('FlashAttention2 installed')"`
3. If installation fails, continue using SDPA - it works fine

### Issue: CUDA Not Available

**Symptoms:**
- Warning: "CUDA not available - will use CPU (slower)"
- Very slow generation

**Solutions:**
1. Install PyTorch with CUDA support:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```
2. Verify CUDA installation: `nvidia-smi`
3. Check PyTorch CUDA: `python -c "import torch; print(torch.cuda.is_available())"`

### Issue: Out of Memory (OOM)

**Symptoms:**
- `RuntimeError: CUDA out of memory`
- Process killed during generation

**Solutions:**
1. Reduce input text length
2. Close other GPU applications
3. Use CPU mode (slower but works):
   ```bash
   CUDA_VISIBLE_DEVICES="" python tests/test_voice_generation.py
   ```
4. Process in smaller chunks

### Issue: Model Download Fails

**Symptoms:**
- `ConnectionError` or timeout during download
- Incomplete model files

**Solutions:**
1. Check internet connection
2. Use Hugging Face CLI with resume:
   ```bash
   huggingface-cli download microsoft/VibeVoice-1.5B --local-dir models/VibeVoice-1.5B --resume-download
   ```
3. Download manually from [Hugging Face](https://huggingface.co/microsoft/VibeVoice-1.5B)

### Issue: Voice Names Not Found

**Symptoms:**
- `Error: Voice not found`
- Available voices list is empty

**Solutions:**
1. Check that voice files exist in `VibeVoice/demo/voices/`
2. Use exact names from the "Available voices" list
3. Common names: `Alice`, `Frank`, `Mary`, `Carter`, `Maya`

### Issue: Inference Script Not Found

**Symptoms:**
- `FileNotFoundError: inference_from_file.py`

**Solutions:**
1. Verify VibeVoice repo is cloned: `ls VibeVoice/demo/`
2. Re-clone the repository:
   ```bash
   rm -rf VibeVoice
   git clone --depth 1 https://github.com/vibevoice-community/VibeVoice.git
   ```

### Issue: Package Installation Fails

**Symptoms:**
- `pip install -e VibeVoice/` fails
- Missing dependencies

**Solutions:**
1. Check Python version: `python --version` (need 3.8+)
2. Upgrade pip: `pip install --upgrade pip`
3. Install build tools:
   - Linux: `sudo apt-get install build-essential`
   - macOS: `xcode-select --install`
4. Check VibeVoice's `pyproject.toml` or `setup.py` for requirements

### Issue: Slow Generation on CPU

**Expected behavior:** CPU generation is 10-50x slower than GPU.

**Solutions:**
1. Use shorter text for testing
2. Consider using cloud GPU (Google Colab, etc.)
3. Wait longer - CPU generation can take several minutes

## Next Steps

After successful setup:

1. **Run the test script:**
   ```bash
   python tests/test_voice_generation.py
   ```

2. **Create custom transcripts:**
   - Edit `tests/sample_transcript.txt`
   - Or create new transcript files

3. **Experiment with different speakers:**
   ```bash
   python tests/test_voice_generation.py Mary Carter
   ```

4. **Explore the VibeVoice repository:**
   - Check `VibeVoice/demo/` for more examples
   - Read the VibeVoice documentation

5. **Start developing:**
   - Plan your API structure in `src/vibevoice/`
   - Design your web interface
   - Write additional tests

## Additional Resources

- [VibeVoice Community Repository](https://github.com/vibevoice-community/VibeVoice)
- [VibeVoice Model Card](https://huggingface.co/microsoft/VibeVoice-1.5B)
- [Hugging Face Documentation](https://huggingface.co/docs)
- [PyTorch Installation Guide](https://pytorch.org/get-started/locally/)

## Getting Help

If you encounter issues not covered here:

1. Check the VibeVoice repository issues
2. Review the beginner's guide: https://www.kdnuggets.com/beginners-guide-to-vibevoice
3. Check Hugging Face model discussions
4. Review error messages carefully - they often contain helpful information
