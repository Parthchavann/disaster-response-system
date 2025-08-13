#!/bin/bash

# NEXUS: Real-Time Multimodal Disaster Intelligence System
# Production Deployment Script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NEXUS_VERSION="1.0.0"
DOCKER_IMAGE="nexus-intelligence"
CONTAINER_NAME="nexus-production"
NETWORK_NAME="nexus-network"
ENV_FILE=".env.production"

# Functions
log_info() {
    echo -e "${BLUE}🔮 NEXUS:${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅ SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}❌ ERROR:${NC} $1"
}

show_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  🔮 NEXUS: Real-Time Multimodal Disaster Intelligence System ║"
    echo "║                    Production Deployment                      ║"
    echo "║                     Version: ${NEXUS_VERSION}                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    log_success "Dependencies check passed"
}

setup_environment() {
    log_info "Setting up environment..."
    
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file $ENV_FILE not found!"
        exit 1
    fi
    
    # Create necessary directories
    mkdir -p logs nginx/ssl
    
    # Set proper permissions
    chmod +x deploy.sh
    
    log_success "Environment setup completed"
}

build_image() {
    log_info "Building NEXUS Docker image..."
    
    docker build -f Dockerfile.nexus -t $DOCKER_IMAGE:$NEXUS_VERSION .
    docker tag $DOCKER_IMAGE:$NEXUS_VERSION $DOCKER_IMAGE:latest
    
    log_success "Docker image built successfully"
}

deploy_production() {
    log_info "Deploying NEXUS to production..."
    
    # Stop existing containers
    docker-compose -f docker-compose.production.yml down --remove-orphans || true
    
    # Start new deployment
    docker-compose -f docker-compose.production.yml up -d
    
    log_success "NEXUS deployed to production"
}

health_check() {
    log_info "Performing health check..."
    
    # Wait for container to start
    sleep 10
    
    local retries=30
    local count=0
    
    while [ $count -lt $retries ]; do
        if curl -f -s http://localhost:8503/api/live-data > /dev/null; then
            log_success "NEXUS is healthy and responding"
            return 0
        fi
        
        log_info "Waiting for NEXUS to start... (attempt $((count + 1))/$retries)"
        sleep 5
        count=$((count + 1))
    done
    
    log_error "Health check failed. NEXUS is not responding."
    return 1
}

show_status() {
    log_info "NEXUS Deployment Status:"
    echo ""
    docker-compose -f docker-compose.production.yml ps
    echo ""
    log_info "Dashboard URL: http://localhost:8503"
    log_info "Health Check: http://localhost:8503/api/live-data"
    echo ""
}

cleanup() {
    log_info "Cleaning up old Docker images..."
    docker image prune -f
    log_success "Cleanup completed"
}

# Main deployment function
main() {
    show_banner
    
    case "${1:-deploy}" in
        "deploy")
            check_dependencies
            setup_environment
            build_image
            deploy_production
            health_check
            show_status
            cleanup
            log_success "🔮 NEXUS deployment completed successfully!"
            echo ""
            echo "Access your NEXUS Intelligence Dashboard at: http://localhost:8503"
            ;;
        "start")
            log_info "Starting NEXUS..."
            docker-compose -f docker-compose.production.yml up -d
            health_check
            show_status
            ;;
        "stop")
            log_info "Stopping NEXUS..."
            docker-compose -f docker-compose.production.yml down
            log_success "NEXUS stopped"
            ;;
        "restart")
            log_info "Restarting NEXUS..."
            docker-compose -f docker-compose.production.yml restart
            health_check
            show_status
            ;;
        "logs")
            docker-compose -f docker-compose.production.yml logs -f
            ;;
        "status")
            show_status
            ;;
        "clean")
            log_info "Cleaning up NEXUS deployment..."
            docker-compose -f docker-compose.production.yml down --volumes --remove-orphans
            docker rmi $DOCKER_IMAGE:latest $DOCKER_IMAGE:$NEXUS_VERSION || true
            cleanup
            log_success "Cleanup completed"
            ;;
        "help")
            echo "NEXUS Deployment Script"
            echo ""
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  deploy   - Full deployment (default)"
            echo "  start    - Start NEXUS services"
            echo "  stop     - Stop NEXUS services"
            echo "  restart  - Restart NEXUS services"
            echo "  logs     - Show live logs"
            echo "  status   - Show deployment status"
            echo "  clean    - Clean up deployment"
            echo "  help     - Show this help message"
            ;;
        *)
            log_error "Unknown command: $1"
            echo "Use '$0 help' for available commands"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"