#!/bin/bash

# DevDocAI Frontend Development Startup Script
# Starts both FastAPI backend and Next.js frontend

echo "🚀 Starting DevDocAI Development Environment..."

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "⚠️  Port $1 is already in use"
        return 1
    else
        return 0
    fi
}

# Function to start FastAPI backend
start_backend() {
    echo "📡 Starting FastAPI Backend on port 8000..."
    cd "$(dirname "$0")/api"

    # Check if Python virtual environment exists
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    pip install -r requirements.txt >/dev/null 2>&1

    # Start FastAPI server
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    echo "✅ Backend started (PID: $BACKEND_PID)"

    # Store PID for cleanup
    echo $BACKEND_PID > ../backend.pid
}

# Function to start Next.js frontend
start_frontend() {
    echo "🌐 Starting Next.js Frontend on port 3000..."
    cd "$(dirname "$0")"

    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        echo "Installing Node.js dependencies..."
        npm install
    fi

    # Start Next.js development server
    npm run dev &
    FRONTEND_PID=$!
    echo "✅ Frontend started (PID: $FRONTEND_PID)"

    # Store PID for cleanup
    echo $FRONTEND_PID > frontend.pid
}

# Function to cleanup processes
cleanup() {
    echo ""
    echo "🧹 Cleaning up processes..."

    if [ -f backend.pid ]; then
        BACKEND_PID=$(cat backend.pid)
        kill $BACKEND_PID 2>/dev/null
        rm backend.pid
        echo "✅ Backend stopped"
    fi

    if [ -f frontend.pid ]; then
        FRONTEND_PID=$(cat frontend.pid)
        kill $FRONTEND_PID 2>/dev/null
        rm frontend.pid
        echo "✅ Frontend stopped"
    fi

    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check if Python is available
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Python is not installed"
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    exit 1
fi

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed"
    exit 1
fi

# Check if ports are available
if ! check_port 8000; then
    echo "❌ Backend port 8000 is in use"
    exit 1
fi

if ! check_port 3000; then
    echo "❌ Frontend port 3000 is in use"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Start services
start_backend
sleep 2  # Give backend time to start

start_frontend
sleep 2  # Give frontend time to start

echo ""
echo "🎉 Development environment is ready!"
echo ""
echo "📡 Backend API: http://localhost:8000"
echo "📡 API Docs: http://localhost:8000/api/docs"
echo "🌐 Frontend: http://localhost:3000"
echo "🎨 Document Studio: http://localhost:3000/studio"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for processes
wait
