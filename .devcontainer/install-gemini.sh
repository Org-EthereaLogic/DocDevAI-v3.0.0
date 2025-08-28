#!/bin/bash
# Install Gemini CLI in container

# Option 1: If Gemini is available via pip
pip install google-generativeai gemini-cli

# Option 2: If Gemini needs to be installed from source
# Uncomment these lines if needed:
# git clone https://github.com/google/gemini-cli.git /tmp/gemini
# cd /tmp/gemini && pip install .

# Option 3: Direct binary download (if available)
# wget https://example.com/gemini-binary -O /usr/local/bin/gemini
# chmod +x /usr/local/bin/gemini

echo "Run 'gemini --help' to test if installation worked"