#!/bin/bash
# Test Docker build locally before deploying to Hugging Face Spaces

echo "🐳 Testing Docker Build for Hugging Face Spaces Deployment"
echo "============================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✅ Docker is installed"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   The Docker container will need PINECONE_API_KEY and GOOGLE_API_KEY"
    echo "   You can pass them with: docker run -e PINECONE_API_KEY=xxx -e GOOGLE_API_KEY=yyy ..."
    echo ""
fi

# Build the Docker image
echo "📦 Building Docker image (this may take 5-10 minutes)..."
echo ""

docker build -t crri-chatbot:test .

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Docker build failed!"
    echo "   Check the error messages above and fix any issues."
    exit 1
fi

echo ""
echo "✅ Docker build successful!"
echo ""

# Ask if user wants to run the container
read -p "🚀 Do you want to run the container locally? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🏃 Starting container on port 7860..."
    echo "   Access the app at: http://localhost:7860"
    echo "   Press Ctrl+C to stop"
    echo ""
    
    # Check if .env exists and load it
    if [ -f .env ]; then
        docker run -p 7860:7860 --env-file .env crri-chatbot:test
    else
        echo "⚠️  Running without .env file - you may need to set environment variables manually"
        docker run -p 7860:7860 crri-chatbot:test
    fi
else
    echo ""
    echo "✅ Build test complete!"
    echo ""
    echo "To run the container later, use:"
    echo "   docker run -p 7860:7860 --env-file .env crri-chatbot:test"
    echo ""
fi

echo ""
echo "🎉 Next steps:"
echo "   1. If the build was successful, you're ready to deploy!"
echo "   2. Follow the instructions in DEPLOYMENT_CHECKLIST.md"
echo "   3. Push your code to Hugging Face Spaces"
echo ""
