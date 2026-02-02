#!/usr/bin/env python3
"""
Verify and report on the AudioMesh API structure.

This script checks if all required files and directories exist.
"""
from pathlib import Path

# Required structure
REQUIRED_FILES = [
    "src/vibevoice/__init__.py",
    "src/vibevoice/config.py",
    "src/vibevoice/main.py",
    "src/vibevoice/middleware/__init__.py",
    "src/vibevoice/middleware/auth.py",
    "src/vibevoice/middleware/rate_limit.py",
    "src/vibevoice/routes/__init__.py",
    "src/vibevoice/routes/speech.py",
    "src/vibevoice/routes/voices.py",
    "src/vibevoice/services/__init__.py",
    "src/vibevoice/services/voice_generator.py",
    "src/vibevoice/services/voice_manager.py",
    "src/vibevoice/models/__init__.py",
    "src/vibevoice/models/schemas.py",
    "src/vibevoice/models/voice_storage.py",
    "run_api.py",
    ".env.example",
]

project_root = Path(__file__).parent

print("Checking AudioMesh API structure...")
print(f"Project root: {project_root}")
print()

missing_files = []
existing_files = []

for file_path in REQUIRED_FILES:
    full_path = project_root / file_path
    if full_path.exists():
        existing_files.append(file_path)
        print(f"✓ {file_path}")
    else:
        missing_files.append(file_path)
        print(f"✗ {file_path} (MISSING)")

print()
print(f"Summary: {len(existing_files)}/{len(REQUIRED_FILES)} files found")

if missing_files:
    print()
    print("Missing files:")
    for file_path in missing_files:
        print(f"  - {file_path}")
    print()
    print("The src/ directory structure is missing.")
    print("You may need to:")
    print("  1. Pull the latest changes: git pull")
    print("  2. Or the files need to be committed and pushed from the development machine")
else:
    print()
    print("All required files are present!")
