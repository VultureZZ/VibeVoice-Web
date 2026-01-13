# VibeVoice Web

A structured project for testing and developing with Microsoft's VibeVoice text-to-speech model. This project provides a foundation for building an API and web interface for voice generation.

## Overview

VibeVoice is an open-source text-to-speech framework designed for generating expressive, long-form, multi-speaker conversational audio. This project uses the community-maintained version and the VibeVoice-1.5B model.

## Features

- Multi-speaker voice generation
- Long-form speech synthesis (up to 90 minutes)
- Natural conversational turn-taking
- Support for English and Chinese
- GPU acceleration (CUDA) for faster generation

## Prerequisites

- Python 3.8 or higher
- Git
- CUDA-capable GPU (recommended, but CPU will work)
- At least 8GB RAM
- ~6GB disk space for the model

## Quick Start

### 1. Clone this repository

```bash
git clone <your-repo-url>
cd VibeVoice-Web
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run setup script

This will clone the VibeVoice repository, download the model, and install the package:

```bash
python scripts/setup_vibevoice.py
```

**Note:** The model download is ~5.4 GB and may take some time depending on your internet connection.

### 5. Run the test script

Generate voice from the sample transcript:

```bash
python tests/test_voice_generation.py
```

Or specify custom speakers:

```bash
python tests/test_voice_generation.py Alice Frank
```

Available speaker names include:
- `Alice` (en-Alice_woman)
- `Frank` (en-Frank_man)
- `Mary` (en-Mary_woman_bgm)
- `Carter` (en-Carter_man)
- `Maya` (en-Maya_woman)
- And more (check the script output for available voices)

The generated audio will be saved in the `outputs/` directory.

## Project Structure

```
VibeVoice-Web/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore patterns
├── src/
│   └── vibevoice/           # Future API code
├── tests/
│   ├── test_voice_generation.py  # Test script
│   └── sample_transcript.txt     # Sample transcript
├── scripts/
│   └── setup_vibevoice.py   # Setup script
├── docs/
│   └── SETUP.md             # Detailed setup guide
├── outputs/                  # Generated audio files
├── models/                   # Downloaded models
└── VibeVoice/               # Cloned VibeVoice repository
```

## Usage

### Generating Voice from Text

1. Create a transcript file with the format:
```
Speaker 1: Your text here.
Speaker 2: Response text here.
Speaker 1: More dialogue.
```

2. Run inference:
```bash
python VibeVoice/demo/inference_from_file.py \
  --model_path models/VibeVoice-1.5B \
  --txt_path path/to/your/transcript.txt \
  --speaker_names Alice Frank
```

### Custom Transcripts

Edit `tests/sample_transcript.txt` or create your own transcript file following the format above.

## Troubleshooting

### CUDA Out of Memory

- Reduce the length of your input text
- Use a smaller batch size if the script supports it
- Close other GPU-intensive applications

### Model Not Found

Run the setup script again:
```bash
python scripts/setup_vibevoice.py
```

### Slow Generation

- Ensure you're using a GPU runtime (CUDA)
- Check GPU availability: `python -c "import torch; print(torch.cuda.is_available())"`
- CPU generation is significantly slower

### Missing Voices

The script will list available voices on startup. Use the exact names shown (e.g., "Alice", "Frank", not "en-Alice_woman").

## Future Development

This project structure is designed to support:

- **API Development**: Add REST API endpoints in `src/vibevoice/`
- **Web Interface**: Build a frontend for voice generation
- **Testing**: Expand test suite in `tests/`
- **Documentation**: Add API documentation in `docs/`

## Resources

- [VibeVoice GitHub](https://github.com/vibevoice-community/VibeVoice)
- [VibeVoice Model on Hugging Face](https://huggingface.co/microsoft/VibeVoice-1.5B)
- [Beginner's Guide](https://www.kdnuggets.com/beginners-guide-to-vibevoice)

## License

This project uses the VibeVoice model, which is licensed under MIT. See the VibeVoice repository for details.

## Disclaimer

VibeVoice is intended for research and development purposes. Please use responsibly and in compliance with all applicable laws and regulations. Always disclose the use of AI when sharing AI-generated content.
