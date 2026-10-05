#!/bin/bash

# ICS31 Quiz Generator - Deployment Script
# Run this after initial EC2 setup to deploy or update the application

set -e

APP_DIR="/opt/quiz-generator"
REPO_URL="${REPO_URL:-https://github.com/YOUR_USERNAME/ICS31_QuizGenerator.git}"

echo "==================================="
echo "ICS31 Quiz Generator - Deploy"
echo "==================================="

cd $APP_DIR

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please create .env with your OPENAI_API_KEY:"
    echo "  echo 'OPENAI_API_KEY=your_key_here' > $APP_DIR/.env"
    exit 1
fi

# Pull latest changes if repo exists, otherwise clone
if [ -d ".git" ]; then
    echo "Pulling latest changes..."
    git pull origin main
else
    echo "Cloning repository..."
    git clone $REPO_URL .
fi

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down || true

# Build and start containers
echo "Building and starting containers..."
docker-compose build --no-cache
docker-compose up -d

# Wait for health check
echo "Waiting for service to be healthy..."
sleep 10

# Check health
if curl -s http://localhost:8000/api/health | grep -q "healthy"; then
    echo ""
    echo "==================================="
    echo "Deployment Successful!"
    echo "==================================="
    echo ""
    echo "Application is running at:"
    echo "  - Local: http://localhost:8000"
    echo "  - Public: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
else
    echo ""
    echo "WARNING: Health check failed. Check logs with:"
    echo "  docker-compose logs -f"
fi
