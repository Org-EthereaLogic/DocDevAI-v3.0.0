#!/bin/bash
set -e

echo "🚀 Setting up DevDocAI Complete Development Environment..."

# Update package list
apt-get update

# Install system dependencies
apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    software-properties-common

# Install Python packages
pip install --upgrade pip
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi

# Install additional Python development tools
pip install \
    black \
    pylint \
    pytest \
    pytest-cov \
    ipython \
    jupyter

# Install Node.js global packages
echo "📦 Installing Node.js tools..."
npm install -g \
    @anthropic-ai/claude-code \
    typescript \
    ts-node \
    nodemon

# Install Gemini CLI (if available via pip)
echo "🤖 Installing AI tools..."
pip install google-generativeai

# Create helpful aliases
cat >> ~/.zshrc << 'EOF'

# DevDocAI Aliases
alias ll='ls -la'
alias gs='git status'
alias py='python'
alias ipy='ipython'
alias test='pytest'
alias format='black .'
alias lint='pylint'

# Project shortcuts
alias devdoc='cd /workspaces/DocDevAI-v3.0.0'
alias run='python src/main.py'

echo "Welcome to DevDocAI Development Environment! 🚀"
echo "Tools available: Python 3.11, Node.js 20, Claude Code, pip, npm"
EOF

# Final message
echo "✅ DevDocAI environment setup complete!"
echo "📝 Available tools:"
echo "  - Python 3.11 with all packages"
echo "  - Node.js 20 with npm"
echo "  - Claude Code CLI (once published)"
echo "  - Git, curl, wget, build tools"
echo ""
echo "🔄 Please rebuild the container to apply these changes:"
echo "  1. Cmd+Shift+P → 'Dev Containers: Rebuild Container'"
echo "  2. Wait for rebuild to complete"
echo "  3. All tools will be available in the VS Code terminal!"