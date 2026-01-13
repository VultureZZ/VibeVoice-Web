#!/usr/bin/env python3
"""
Run script for VibeVoice API.

This script sets up the Python path and runs the FastAPI application.
"""
import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Now import and run the app
if __name__ == "__main__":
    import uvicorn
    from vibevoice.config import config

    uvicorn.run(
        "vibevoice.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
    )
