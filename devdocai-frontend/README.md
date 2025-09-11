# DevDocAI Frontend

Modern web interface for DevDocAI v3.0.0 - AI-powered documentation generation system.

## Architecture

- **Frontend**: Next.js 15 with TypeScript and Tailwind CSS
- **Backend Bridge**: FastAPI server that connects to DevDocAI Python core
- **API Integration**: RESTful communication between frontend and AI modules

## Quick Start

### Option 1: Automated Startup (Recommended)

```bash
# Start both backend and frontend
./start-dev.sh
```

This will start:
- FastAPI backend on port 8000
- Next.js frontend on port 3000

### Option 2: Manual Startup

**Backend (Terminal 1):**
```bash
cd api
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend (Terminal 2):**
```bash
npm install
npm run dev
```

## Access Points

- **Frontend**: http://localhost:3000
- **Document Studio**: http://localhost:3000/studio
- **API Documentation**: http://localhost:8000/api/docs
- **API Health**: http://localhost:8000

## Features

### Landing Page (/)
- Hero section with live demo
- Feature showcase with real performance metrics
- Call-to-action sections
- Professional design system

### Document Studio (/studio)
- 3-step workflow: Generate → Enhance → Analyze
- Template selection from DevDocAI core
- Real-time AI processing with MIAIR engine
- Quality analysis with entropy scoring
- Progress tracking and visual feedback

## API Integration

The frontend communicates with the FastAPI backend bridge, which connects to:

- **M004 Document Generator**: AI-powered content generation
- **M009 Enhancement Pipeline**: MIAIR quality improvement
- **M007 Review Engine**: Multi-dimensional analysis
- **M013 Template Marketplace**: Community templates

## Development

### Project Structure

```
devdocai-frontend/
├── src/
│   ├── app/                 # Next.js app router pages
│   ├── components/          # Reusable UI components
│   └── lib/                 # Utilities and API client
├── api/                     # FastAPI backend bridge
└── public/                  # Static assets
```

### Key Components

- **Landing Page**: Modern marketing site with live demo
- **Document Studio**: Full-featured document generation interface
- **API Client**: TypeScript client for backend communication
- **Loading Components**: Professional loading states and spinners

### Demo Mode

The system includes demo mode fallbacks when the Python DevDocAI core is not available:

- Generated sample content for demonstrations
- Mock API responses for development
- Graceful degradation for offline development

## Technology Stack

- **Next.js 15**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **FastAPI**: Python backend bridge
- **DevDocAI Core**: AI-powered documentation engine

## Production Deployment

For production deployment, the FastAPI backend should connect to a properly configured DevDocAI Python environment with:

- API keys for LLM providers (OpenAI, Anthropic, Google)
- Encrypted local storage configuration
- Template marketplace access
- Performance optimization settings

## Contributing

This frontend is part of the DevDocAI v3.0.0 project. See the main project README for contribution guidelines and development setup.
