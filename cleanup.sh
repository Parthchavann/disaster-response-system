#!/bin/bash

# Cleanup Script for Disaster Response System
# Stops all services and cleans up resources

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_info "🧹 Starting cleanup of Disaster Response System..."

# Stop Python processes
if [ -f .pids ]; then
    log_info "   Stopping application processes..."
    PIDS=$(cat .pids)
    for pid in $PIDS; do
        if kill -0 $pid 2>/dev/null; then
            log_info "   Stopping process $pid..."
            kill $pid 2>/dev/null || true
            sleep 2
            # Force kill if still running
            if kill -0 $pid 2>/dev/null; then
                kill -9 $pid 2>/dev/null || true
            fi
        fi
    done
    rm .pids
    log_info "   ✅ Application processes stopped"
fi

# Stop any remaining Python processes related to our project
log_info "   Checking for remaining Python processes..."
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "streamlit run app.py" 2>/dev/null || true
pkill -f "mlflow server" 2>/dev/null || true
pkill -f "kafka_producer.py" 2>/dev/null || true
pkill -f "spark_streaming.py" 2>/dev/null || true

# Stop Docker services
log_info "   Stopping Docker services..."
if [ -f docker-compose.yml ]; then
    docker-compose down --remove-orphans
    log_info "   ✅ Docker services stopped"
else
    log_warn "   docker-compose.yml not found, skipping Docker cleanup"
fi

# Clean up temporary files
log_info "   Cleaning up temporary files..."
rm -f .env
rm -rf __pycache__
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Clean up logs
if [ -d logs ]; then
    rm -rf logs
fi

# Optional: Clean up Docker volumes and networks (uncomment if needed)
# log_info "   Cleaning up Docker volumes..."
# docker-compose down -v
# docker system prune -f

log_info "✅ Cleanup completed successfully!"
log_info ""
log_info "🔄 To restart the system, run:"
log_info "   ./setup_and_run.sh"
log_info ""