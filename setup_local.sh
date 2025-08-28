#!/bin/bash
# Setup script for local development (without container)

echo "Setting up DevDocAI for local development..."

# Create Python virtual environment
python3.11 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

echo "✅ Local environment ready!"
echo "To activate: source venv/bin/activate"
echo "Claude and Gemini work normally in this terminal"