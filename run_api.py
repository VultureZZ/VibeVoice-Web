#!/usr/bin/env python3
"""
Run script for VibeVoice API.

This script sets up the Python path and runs the FastAPI application.
"""
import os
import sys
from pathlib import Path

# Add src directory to Python path BEFORE any imports
project_root = Path(__file__).parent.resolve()
src_path = project_root / "src"

# Verify src directory exists
if not src_path.exists():
    print(f"Error: Source directory not found: {src_path}")
    print(f"Current directory: {Path.cwd()}")
    sys.exit(1)

# Add to Python path
src_path_str = str(src_path)
if src_path_str not in sys.path:
    sys.path.insert(0, src_path_str)

# Also set PYTHONPATH environment variable for uvicorn reload
os.environ["PYTHONPATH"] = src_path_str + os.pathsep + os.environ.get("PYTHONPATH", "")

# Now import and run the app
if __name__ == "__main__":
    # Check for required dependencies
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is not installed.")
        print("Please install dependencies: pip install -r requirements.txt")
        sys.exit(1)
    
    try:
        # Import after path is set - import the app object directly
        from vibevoice.main import app
        from vibevoice.config import config
    except ImportError as e:
        print(f"Error: Failed to import vibevoice module: {e}")
        print(f"Python path: {sys.path}")
        print(f"Looking for module in: {src_path}")
        print("\nMake sure:")
        print("1. Dependencies are installed: pip install -r requirements.txt")
        print("2. You're running from the project root directory")
        sys.exit(1)

    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        reload=True,
        reload_dirs=[str(project_root / "src")],
    )
