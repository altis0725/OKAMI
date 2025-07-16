#!/bin/bash
# Test script for Docker environment

set -e

echo "🚀 Starting OKAMI Docker tests..."

# Clean up any existing containers
echo "📦 Cleaning up existing containers..."
docker-compose -f docker-compose.yaml down --volumes --remove-orphans 2>/dev/null || true
docker-compose -f docker-compose.test.yaml down --volumes --remove-orphans 2>/dev/null || true

# Build the images
echo "🔨 Building Docker images..."
docker-compose -f docker-compose.yaml build

# Start services
echo "🏃 Starting OKAMI services..."
docker-compose -f docker-compose.yaml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check health
echo "🏥 Checking service health..."
if curl -f http://localhost:8000/health; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    docker-compose -f docker-compose.yaml logs
    docker-compose -f docker-compose.yaml down
    exit 1
fi

# Check status
echo "📊 Checking system status..."
curl -s http://localhost:8000/status | python -m json.tool

# List available crews
echo "👥 Listing available crews..."
curl -s http://localhost:8000/crews | python -m json.tool

# Test task execution
echo "🧪 Testing task execution..."
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "crew_name": "main_crew",
    "task": "Test the OKAMI system",
    "async_execution": false
  }' | python -m json.tool

# Check logs
echo "📜 Recent logs from OKAMI service..."
docker-compose -f docker-compose.yaml logs --tail=20 okami

# Clean up
echo "🧹 Cleaning up..."
docker-compose -f docker-compose.yaml down

echo "✅ Docker tests completed successfully!"