#!/bin/bash

# Frappe-Supabase Sync Service Deployment Script

set -e

echo "🚀 Starting Frappe-Supabase Sync Service Deployment"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Load environment variables
export $(cat .env | xargs)

# Validate required environment variables
required_vars=("FRAPPE_URL" "FRAPPE_API_KEY" "FRAPPE_API_SECRET" "SUPABASE_URL" "SUPABASE_SERVICE_ROLE_KEY" "WEBHOOK_SECRET_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set."
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Create necessary directories
mkdir -p logs
mkdir -p data/redis
mkdir -p data/postgres

echo "✅ Directories created"

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🔍 Checking service health..."
max_attempts=10
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Service is healthy!"
        break
    else
        echo "⏳ Attempt $attempt/$max_attempts - Service not ready yet..."
        sleep 10
        ((attempt++))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ Service failed to start properly. Check logs with: docker-compose logs"
    exit 1
fi

# Display service information
echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📊 Service Information:"
echo "  - Sync Service: http://localhost:8000"
echo "  - Health Check: http://localhost:8000/health"
echo "  - Metrics: http://localhost:8000/metrics"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "📈 Monitoring:"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
echo "  - Prometheus: http://localhost:9090"
echo ""
echo "🔧 Management Commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart services: docker-compose restart"
echo "  - Update services: docker-compose pull && docker-compose up -d"
echo ""
echo "📋 Next Steps:"
echo "  1. Configure webhooks in Frappe and Supabase"
echo "  2. Set up sync mappings via API or configuration"
echo "  3. Monitor service health and metrics"
echo "  4. Test synchronization with sample data"
echo ""

# Show current status
echo "📊 Current Status:"
curl -s http://localhost:8000/sync/status | jq '.' 2>/dev/null || echo "  (Install jq for formatted output)"
