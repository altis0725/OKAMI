#!/bin/bash
# Production deployment script for OKAMI

set -e

echo "🚀 Starting OKAMI production deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy env.example to .env and configure it"
    exit 1
fi

# Check if SSL certificates exist
if [ ! -f nginx/ssl/cert.pem ] || [ ! -f nginx/ssl/key.pem ]; then
    echo "⚠️  Warning: SSL certificates not found in nginx/ssl/"
    echo "Generating self-signed certificates for testing..."
    mkdir -p nginx/ssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/key.pem \
        -out nginx/ssl/cert.pem \
        -subj "/C=US/ST=State/L=City/O=OKAMI/CN=localhost"
fi

# Pull latest changes (if in git repo)
if [ -d .git ]; then
    echo "📦 Pulling latest changes..."
    git pull origin main || true
fi

# Build images
echo "🔨 Building Docker images..."
docker-compose -f docker-compose.prod.yaml build

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.prod.yaml down

# Start services
echo "🏃 Starting production services..."
docker-compose -f docker-compose.prod.yaml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check health
echo "🏥 Checking service health..."
if curl -k -f https://localhost/health; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    echo "📜 Showing logs..."
    docker-compose -f docker-compose.prod.yaml logs --tail=50
    exit 1
fi

# Show running services
echo "📊 Running services:"
docker-compose -f docker-compose.prod.yaml ps

echo "✅ Production deployment completed!"
echo ""
echo "🌐 OKAMI is now running at https://localhost"
echo "📊 Monitoring dashboard: http://localhost:8001"
echo ""
echo "📝 To view logs: docker-compose -f docker-compose.prod.yaml logs -f"
echo "🛑 To stop: docker-compose -f docker-compose.prod.yaml down"