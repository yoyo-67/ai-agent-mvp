#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================="
echo "  AI Agent MVP - Startup Script"
echo "========================================="
echo ""

# --- Check Python ---
echo "Checking Python..."
PYTHON_CMD=""

# Try to find Python 3.11+ (check specific versions first)
for cmd in python3.13 python3.12 python3.11 python3; do
    if command -v $cmd &> /dev/null; then
        VERSION=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        MAJOR=$(echo $VERSION | cut -d. -f1)
        MINOR=$(echo $VERSION | cut -d. -f2)

        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ]; then
            PYTHON_CMD=$cmd
            break
        fi
    fi
done

if [ -n "$PYTHON_CMD" ]; then
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo -e "${GREEN}✓ Python $PYTHON_VERSION found ($PYTHON_CMD)${NC}"
else
    echo -e "${RED}✗ Python 3.11+ not found${NC}"
    echo "  Please install Python 3.11 or higher"
    echo "  macOS: brew install python@3.11"
    echo "  Ubuntu: sudo apt install python3.11"
    exit 1
fi

# --- Check Node.js ---
echo "Checking Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)

    if [ "$NODE_VERSION" -ge 18 ]; then
        echo -e "${GREEN}✓ Node.js v$(node -v | sed 's/v//') found${NC}"
    else
        echo -e "${RED}✗ Node.js 18+ required, found v$(node -v | sed 's/v//')${NC}"
        echo "  Please install Node.js 18 or higher"
        echo "  https://nodejs.org/"
        exit 1
    fi
else
    echo -e "${RED}✗ Node.js not found${NC}"
    echo "  Please install Node.js 18 or higher"
    echo "  https://nodejs.org/"
    exit 1
fi

# --- Check uv (optional but recommended) ---
echo "Checking uv..."
USE_UV=false
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✓ uv found (will use for faster installs)${NC}"
    USE_UV=true
else
    echo -e "${YELLOW}! uv not found, will use pip instead${NC}"
    echo "  For faster installs, consider: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

echo ""
echo "========================================="
echo "  Setting up Backend"
echo "========================================="

cd "$SCRIPT_DIR/backend"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    $PYTHON_CMD -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
if [ "$USE_UV" = true ]; then
    uv pip install -e .
else
    pip install -e .
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo -e "${YELLOW}! .env file not found${NC}"

    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  Created .env from .env.example"
    else
        echo "OPENAI_API_KEY=" > .env
        echo "  Created empty .env file"
    fi

    echo ""
    echo -e "${YELLOW}Please set your OpenAI API key:${NC}"
    read -p "  Enter your OPENAI_API_KEY (or press Enter to skip): " API_KEY

    if [ -n "$API_KEY" ]; then
        echo "OPENAI_API_KEY=$API_KEY" > .env
        echo -e "${GREEN}✓ API key saved to .env${NC}"
    else
        echo -e "${YELLOW}! Remember to set OPENAI_API_KEY in backend/.env before using the app${NC}"
    fi
fi

echo ""
echo "========================================="
echo "  Setting up Frontend"
echo "========================================="

cd "$SCRIPT_DIR/frontend"

# Install npm dependencies
echo "Installing npm dependencies..."
npm install

echo ""
echo "========================================="
echo "  Starting Services"
echo "========================================="
echo ""

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "Shutting down services..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "Starting backend on http://localhost:8002..."
cd "$SCRIPT_DIR/backend"
source .venv/bin/activate
uvicorn main:app --reload --port 8002 > "$SCRIPT_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start frontend
echo "Starting frontend on http://localhost:3000..."
cd "$SCRIPT_DIR/frontend"
npm run dev > "$SCRIPT_DIR/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  Services Started!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8002"
echo ""
echo "  Logs:"
echo "    tail -f logs/backend.log"
echo "    tail -f logs/frontend.log"
echo ""
echo "  Press Ctrl+C to stop all services"
echo ""

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
