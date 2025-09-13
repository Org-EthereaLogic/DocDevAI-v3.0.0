# DevDocAI Frontend Prototype

A minimal Vue 3 frontend prototype for DevDocAI v3.0.0 - an AI-powered documentation generator.

## Features

- ✅ Vue 3 with Composition API
- ✅ Vite for fast development
- ✅ Tailwind CSS for styling
- ✅ Axios for API communication
- ✅ Real-time AI document generation
- ✅ Markdown preview and raw view
- ✅ Loading states with progress indicators
- ✅ Copy to clipboard and download functionality

## Quick Start

### Prerequisites

- Node.js 18+ installed
- Backend API running on http://localhost:8000

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at http://localhost:5173

### Backend Setup

Make sure the FastAPI backend is running:

```bash
cd /Users/etherealogic/Dev/DocDevAI-v3.0.0
source .venv/bin/activate
python run_api.py
```

## Usage

1. Fill in the form with your project details
2. Click "Generate README" to create documentation
3. Wait 60-90 seconds for AI generation
4. View, copy, or download the generated README

## Technologies Used

- **Vue 3** - Progressive JavaScript framework
- **Vite** - Next generation frontend tooling
- **Tailwind CSS** - Utility-first CSS framework
- **Axios** - Promise-based HTTP client
- **Marked** - Markdown parser and renderer
