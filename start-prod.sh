# Production startup script
#!/bin/bash

echo "🚀 Starting FastAPI Authentication & Background Jobs Demo (Production)"
echo "=================================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it with production configuration."
    exit 1
fi

# Build and start all services
echo "🐳 Building and starting all services..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 15

# Check service health
echo "🏥 Checking service health..."
docker-compose ps

# Show logs
echo "📋 Service logs:"
docker-compose logs --tail=50

echo ""
echo "✅ Services started successfully!"
echo "API: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "RabbitMQ Management: http://localhost:15672"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop services: docker-compose down"
