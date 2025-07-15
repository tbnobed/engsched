#!/bin/bash

# TBN Engineering Technician Scheduler - Docker Deployment Script
# This script automates the deployment process for the application

set -e

echo "=== TBN Engineering Technician Scheduler Deployment ==="
echo "Starting deployment process..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Please copy .env.example to .env and configure your environment variables:"
    echo "  cp .env.example .env"
    echo "  nano .env  # Edit the configuration"
    exit 1
fi

# Verify required environment variables
echo "📋 Checking environment configuration..."
source .env

required_vars=(
    "POSTGRES_USER"
    "POSTGRES_PASSWORD" 
    "POSTGRES_DB"
    "FLASK_SECRET_KEY"
    "DATABASE_URL"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set in .env"
        exit 1
    fi
done

echo "✅ Environment configuration looks good!"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

echo "🔄 Stopping existing containers..."
docker-compose down

echo "🏗️  Building application image..."
docker-compose build --no-cache

echo "🚀 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are healthy
echo "🔍 Checking service health..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    attempt=$((attempt+1))
    
    if docker-compose ps | grep -q "Up (healthy)"; then
        echo "✅ Services are healthy!"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ Services failed to become healthy after $max_attempts attempts"
        echo "Check the logs with: docker-compose logs"
        exit 1
    fi
    
    echo "Attempt $attempt/$max_attempts - waiting for services to be healthy..."
    sleep 5
done

echo "🎉 Deployment completed successfully!"
echo ""
echo "Your application is now running at:"
echo "  🌐 http://localhost:5000"
echo ""
echo "Useful commands:"
echo "  📊 View logs: docker-compose logs -f"
echo "  🛑 Stop services: docker-compose down"
echo "  🔄 Restart services: docker-compose restart"
echo "  💾 View database: docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB"
echo ""
echo "🔒 Security Notes:"
echo "  • Ensure your .env file is not committed to version control"
echo "  • Use strong passwords for database credentials"
echo "  • Keep your SendGrid API key secure"
echo "  • Regularly backup your database using the backup volume"