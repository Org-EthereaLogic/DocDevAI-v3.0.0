#!/usr/bin/env python
"""
Run the DevDocAI FastAPI server.
Usage: python run_api.py
"""

import os
import sys

import uvicorn

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Configure and run the server
    uvicorn.run(
        "devdocai.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True,
    )
