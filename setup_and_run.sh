#!/bin/bash

# Complete Setup and Run Script for Disaster Response System
# This script will install dependencies, set up the environment, and run the entire system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${BLUE}$1${NC}"
}

# Print banner
print_banner() {
    log_header "============================================================"
    log_header "🚨 DISASTER RESPONSE SYSTEM - COMPLETE SETUP & DEPLOYMENT"
    log_header "============================================================"
    echo ""
}

# Check if running in WSL
check_wsl() {
    if grep -qi microsoft /proc/version; then
        log_info "🐧 Running in WSL environment"
        export WSL_ENV=true
    else
        export WSL_ENV=false
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "🔍 Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_info "   Python version: $PYTHON_VERSION"
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is not installed"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        log_info "   Install from: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Test Docker daemon
    if ! docker ps &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    log_info "✅ All prerequisites satisfied"
}

# Install Python dependencies
install_dependencies() {
    log_info "📦 Installing Python dependencies..."
    
    # Upgrade pip
    python3 -m pip install --upgrade pip
    
    # Install main requirements
    if [ -f "requirements.txt" ]; then
        log_info "   Installing main requirements..."
        pip3 install -r requirements.txt
    else
        log_error "requirements.txt not found"
        exit 1
    fi
    
    # Install frontend requirements
    if [ -f "frontend/requirements-frontend.txt" ]; then
        log_info "   Installing frontend requirements..."
        pip3 install -r frontend/requirements-frontend.txt
    fi
    
    log_info "✅ Dependencies installed successfully"
}

# Setup environment
setup_environment() {
    log_info "⚙️ Setting up environment..."
    
    # Create necessary directories
    mkdir -p logs data models checkpoints
    
    # Set environment variables
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
    export REDIS_HOST="localhost"
    export QDRANT_HOST="localhost"
    export API_HOST="0.0.0.0"
    export API_PORT="8000"
    export FRONTEND_PORT="8501"
    
    # Create .env file
    cat > .env << EOF
PYTHONPATH=${PYTHONPATH}:$(pwd)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_HOST=localhost
REDIS_PORT=6379
QDRANT_HOST=localhost
QDRANT_PORT=6333
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_PORT=8501
LOG_LEVEL=INFO
EOF
    
    log_info "✅ Environment configured"
}

# Start Docker services
start_docker_services() {
    log_info "🐳 Starting Docker services..."
    
    # Pull images first
    docker-compose pull
    
    # Start services
    docker-compose up -d
    
    # Wait for services to be ready
    log_info "   Waiting for services to be ready..."
    
    # Wait for Kafka
    log_info "   Waiting for Kafka..."
    timeout=60
    while ! docker-compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list &> /dev/null; do
        sleep 2
        timeout=$((timeout-2))
        if [ $timeout -le 0 ]; then
            log_error "Kafka failed to start within timeout"
            docker-compose logs kafka
            exit 1
        fi
    done
    log_info "   ✅ Kafka is ready"
    
    # Wait for Redis
    log_info "   Waiting for Redis..."
    timeout=30
    while ! docker-compose exec -T redis redis-cli ping &> /dev/null; do
        sleep 1
        timeout=$((timeout-1))
        if [ $timeout -le 0 ]; then
            log_error "Redis failed to start within timeout"
            docker-compose logs redis
            exit 1
        fi
    done
    log_info "   ✅ Redis is ready"
    
    # Wait for Qdrant
    log_info "   Waiting for Qdrant..."
    timeout=30
    while ! curl -s http://localhost:6333/collections &> /dev/null; do
        sleep 1
        timeout=$((timeout-1))
        if [ $timeout -le 0 ]; then
            log_error "Qdrant failed to start within timeout"
            docker-compose logs qdrant
            exit 1
        fi
    done
    log_info "   ✅ Qdrant is ready"
    
    log_info "✅ All Docker services are ready"
}

# Initialize ML models
initialize_models() {
    log_info "🤖 Initializing ML models..."
    
    # This creates basic model structures - in production you'd load pre-trained models
    log_info "   Setting up model directories..."
    mkdir -p models/text_classifier models/image_classifier models/multimodal_fusion
    
    log_info "✅ Models initialized"
}

# Create demo data
create_demo_data() {
    log_info "📊 Creating demo data..."
    
    # Wait for backend to be ready
    timeout=60
    while ! curl -s http://localhost:8000/health &> /dev/null; do
        sleep 2
        timeout=$((timeout-2))
        if [ $timeout -le 0 ]; then
            log_warn "Backend not ready for demo data"
            return
        fi
    done
    
    # Create a sample disaster event
    curl -X POST "http://localhost:8000/predict" \
         -H "Content-Type: application/json" \
         -d '{
           "text": "URGENT: Major flooding in downtown area, water levels rising rapidly!",
           "location": {"lat": 37.7749, "lon": -122.4194},
           "weather_data": {
             "wind_speed_mph": 45.0,
             "precipitation_mm": 75.0,
             "is_extreme": true
           }
         }' &> /dev/null || log_warn "Could not create demo data"
    
    log_info "✅ Demo data created"
}

# Start application services
start_applications() {
    log_info "🚀 Starting application services..."
    
    # Start data ingestion in background
    log_info "   Starting data ingestion..."
    python3 data-ingestion/kafka_producer.py &
    KAFKA_PRODUCER_PID=$!
    
    # Start backend API
    log_info "   Starting backend API..."
    cd backend
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    cd ..
    
    # Wait for backend to be ready
    log_info "   Waiting for backend API..."
    timeout=60
    while ! curl -s http://localhost:8000/health &> /dev/null; do
        sleep 2
        timeout=$((timeout-2))
        if [ $timeout -le 0 ]; then
            log_error "Backend API failed to start"
            kill $BACKEND_PID $KAFKA_PRODUCER_PID 2>/dev/null || true
            exit 1
        fi
    done
    log_info "   ✅ Backend API is ready"
    
    # Start MLflow server
    log_info "   Starting MLflow server..."
    cd mlops
    python3 -m mlflow server --host 0.0.0.0 --port 5000 &
    MLFLOW_PID=$!
    cd ..
    
    # Start frontend dashboard
    log_info "   Starting frontend dashboard..."
    cd frontend
    python3 -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
    FRONTEND_PID=$!
    cd ..
    
    # Wait for frontend
    log_info "   Waiting for frontend dashboard..."
    timeout=60
    while ! curl -s http://localhost:8501 &> /dev/null; do
        sleep 2
        timeout=$((timeout-2))
        if [ $timeout -le 0 ]; then
            log_warn "Frontend dashboard took longer than expected to start"
            break
        fi
    done
    
    # Store PIDs for cleanup
    echo "$KAFKA_PRODUCER_PID $BACKEND_PID $MLFLOW_PID $FRONTEND_PID" > .pids
    
    log_info "✅ All application services started"
}

# Print access information
print_access_info() {
    log_header ""
    log_header "🎉 DISASTER RESPONSE SYSTEM IS NOW RUNNING!"
    log_header ""
    
    echo -e "${GREEN}📡 Service Access URLs:${NC}"
    echo -e "   🌐 Frontend Dashboard:  ${BLUE}http://localhost:8501${NC}"
    echo -e "   🔌 Backend API:         ${BLUE}http://localhost:8000${NC}"
    echo -e "   📚 API Documentation:   ${BLUE}http://localhost:8000/docs${NC}"
    echo -e "   🧪 MLflow Tracking:     ${BLUE}http://localhost:5000${NC}"
    echo -e "   ❤️  Health Check:       ${BLUE}http://localhost:8000/health${NC}"
    
    echo ""
    echo -e "${GREEN}🎯 Quick Start Guide:${NC}"
    echo "   1. Open http://localhost:8501 for the main dashboard"
    echo "   2. Navigate to 'Predictions' tab to test disaster detection"
    echo "   3. Try the 'Event Analysis' tab for monitoring"
    echo "   4. Check 'Search' tab to find similar events"
    echo "   5. Use 'Settings' tab for system configuration"
    
    echo ""
    echo -e "${GREEN}🔧 System Management:${NC}"
    echo "   • Press Ctrl+C to shutdown gracefully"
    echo "   • Check logs with: docker-compose logs [service]"
    echo "   • Restart with: ./setup_and_run.sh"
    echo "   • Clean shutdown: ./cleanup.sh"
    
    echo ""
    echo -e "${GREEN}📊 Docker Services Status:${NC}"
    docker-compose ps
    
    log_header ""
    log_header "System is ready! Visit http://localhost:8501 to get started."
    log_header ""
}

# Cleanup function
cleanup() {
    log_info "🧹 Cleaning up..."
    
    # Kill application processes
    if [ -f .pids ]; then
        PIDS=$(cat .pids)
        for pid in $PIDS; do
            kill $pid 2>/dev/null || true
        done
        rm .pids
    fi
    
    # Stop Docker services
    docker-compose down
    
    log_info "✅ Cleanup complete"
}

# Trap signals for cleanup
trap cleanup EXIT INT TERM

# Main execution
main() {
    print_banner
    check_wsl
    check_prerequisites
    install_dependencies
    setup_environment
    start_docker_services
    initialize_models
    start_applications
    create_demo_data
    print_access_info
    
    # Keep script running
    log_info "🔄 System is running. Press Ctrl+C to stop."
    while true; do
        sleep 10
        
        # Check if services are still running
        if ! curl -s http://localhost:8000/health &> /dev/null; then
            log_error "Backend API is not responding"
            break
        fi
    done
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi