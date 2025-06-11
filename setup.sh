#!/bin/bash

# AudioBook Converter - Project Setup Script
# This script helps you set up the development environment

echo "🎧 AudioBook Converter - Setup Script"
echo "======================================"

# Check if required tools are installed
check_tool() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 is not installed. Please install it first."
        return 1
    else
        echo "✅ $1 is installed"
        return 0
    fi
}

echo ""
echo "🔍 Checking system requirements..."

# Check required tools
check_tool "node" || exit 1
check_tool "npm" || exit 1
check_tool "python3" || exit 1
check_tool "pip3" || exit 1
check_tool "docker" || echo "⚠️  Docker not found. You can still run without Docker."
check_tool "docker-compose" || echo "⚠️  Docker Compose not found. You can still run without Docker."

echo ""
echo "📦 Setting up backend..."

# Create virtual environment and install dependencies
cd backend
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Creating uploads and audio_output directories..."
mkdir -p uploads audio_output

# Copy environment file
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit backend/.env and add your API keys"
fi

cd ..

echo ""
echo "📱 Setting up mobile app..."

# Setup React Native app
cd mobile

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
else
    echo "Node modules already installed"
fi

# Create basic mobile environment file
if [ ! -f ".env" ]; then
    echo "Creating mobile .env file..."
    cat > .env << EOF
API_BASE_URL=http://localhost:8000
EOF
fi

cd ..

echo ""
echo "🐳 Docker setup..."

# Create docker directories
mkdir -p ./uploads ./audio_output

if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "Docker and Docker Compose are available."
    echo "You can run: docker-compose up -d to start all services"
else
    echo "Docker not available. You'll need to run services manually."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Next steps:"
echo "1. Configure your API keys in backend/.env"
echo "   - Get Gemini API key from: https://ai.google.dev/"
echo ""
echo "2. Choose how to run the project:"
echo ""
echo "   Option A - Using Docker (Recommended):"
echo "   docker-compose up -d"
echo ""
echo "   Option B - Manual setup:"
echo "   # Terminal 1: Start PostgreSQL and Redis"
echo "   # Terminal 2: Start backend"
echo "   cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo "   # Terminal 3: Start mobile app"
echo "   cd mobile && npm start"
echo ""
echo "3. API Documentation will be available at: http://localhost:8000/docs"
echo "4. Mobile app can be run with: npm run android or npm run ios"
echo ""
echo "📖 For detailed setup instructions, see README.md" 