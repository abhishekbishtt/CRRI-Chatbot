#!/bin/bash
# Test Docker build locally before deploying to Hugging Face Spaces

echo "Testing Docker Build for Hugging Face Spaces Deployment"
echo "============================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

echo "Docker is installed"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found"
    echo "The Docker container will need PINECONE_API_KEY and GOOGLE_API_KEY"
    echo ""
fi

# Build the Docker image
echo "Building Docker image..."
echo ""

docker build -t crri-chatbot:test .

if [ $? -ne 0 ]; then
    echo ""
    echo "Docker build failed!"
    exit 1
fi

echo ""
echo "Docker build successful!"
echo ""

# Ask if user wants to run the container
read -p "Do you want to run the container locally? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting container on port 7860..."
    echo "Access the app at: http://localhost:7860"
    echo "Press Ctrl+C to stop"
    echo ""
    
    # Check if .env exists and load it
    if [ -f .env ]; then
        docker run -p 7860:7860 --env-file .env crri-chatbot:test
    else
        echo "Running without .env file"
        docker run -p 7860:7860 crri-chatbot:test
    fi
else
    echo ""
    echo "Build test complete!"
    echo ""
    echo "To run the container later, use:"
    echo "   docker run -p 7860:7860 --env-file .env crri-chatbot:test"
    echo ""
fi
