#!/bin/bash

# Bot deployment script
echo "=== DEPLOYING TELEGRAM BOT ==="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Build and run with Docker Compose
echo "Building Docker image..."
docker-compose build

echo "Starting bot container..."
docker-compose up -d

echo "Checking status..."
docker-compose ps

echo "=== BOT DEPLOYED SUCCESSFULLY ==="
echo "View logs: docker-compose logs -f bot"
echo "Stop bot: docker-compose down"
