#!/bin/bash

# Disaster Response System Deployment Script
# Supports AWS, GCP, and Azure deployments

set -e

# Configuration
CLUSTER_NAME="disaster-response-cluster"
NAMESPACE="disaster-response"
ENVIRONMENT=${ENVIRONMENT:-"production"}
CLOUD_PROVIDER=${CLOUD_PROVIDER:-"aws"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    commands=("kubectl" "docker" "terraform")
    
    for cmd in "${commands[@]}"; do
        if ! command -v $cmd &> /dev/null; then
            log_error "$cmd is not installed or not in PATH"
            exit 1
        fi
    done
    
    # Check cloud-specific CLI tools
    case $CLOUD_PROVIDER in
        "aws")
            if ! command -v aws &> /dev/null; then
                log_error "AWS CLI is not installed"
                exit 1
            fi
            ;;
        "gcp")
            if ! command -v gcloud &> /dev/null; then
                log_error "Google Cloud CLI is not installed"
                exit 1
            fi
            ;;
        "azure")
            if ! command -v az &> /dev/null; then
                log_error "Azure CLI is not installed"
                exit 1
            fi
            ;;
    esac
    
    log_info "All prerequisites satisfied"
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    
    # Build backend image
    log_info "Building backend image..."
    docker build -t disaster-response/backend:latest ./backend/
    
    # Build frontend image
    log_info "Building frontend image..."
    docker build -t disaster-response/frontend:latest ./frontend/
    
    # Tag images for cloud registry
    case $CLOUD_PROVIDER in
        "aws")
            ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
            REGION=${AWS_DEFAULT_REGION:-us-west-2}
            REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
            
            # Create ECR repositories if they don't exist
            aws ecr describe-repositories --repository-names disaster-response/backend --region $REGION || \
                aws ecr create-repository --repository-name disaster-response/backend --region $REGION
            aws ecr describe-repositories --repository-names disaster-response/frontend --region $REGION || \
                aws ecr create-repository --repository-name disaster-response/frontend --region $REGION
            
            # Login to ECR
            aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY
            
            # Tag and push images
            docker tag disaster-response/backend:latest $REGISTRY/disaster-response/backend:latest
            docker tag disaster-response/frontend:latest $REGISTRY/disaster-response/frontend:latest
            docker push $REGISTRY/disaster-response/backend:latest
            docker push $REGISTRY/disaster-response/frontend:latest
            ;;
        "gcp")
            PROJECT_ID=$(gcloud config get-value project)
            REGISTRY="gcr.io/$PROJECT_ID"
            
            # Configure Docker to use gcloud as credential helper
            gcloud auth configure-docker
            
            # Tag and push images
            docker tag disaster-response/backend:latest $REGISTRY/disaster-response/backend:latest
            docker tag disaster-response/frontend:latest $REGISTRY/disaster-response/frontend:latest
            docker push $REGISTRY/disaster-response/backend:latest
            docker push $REGISTRY/disaster-response/frontend:latest
            ;;
        "azure")
            REGISTRY_NAME="disasterresponseregistry"
            REGISTRY="${REGISTRY_NAME}.azurecr.io"
            
            # Login to ACR
            az acr login --name $REGISTRY_NAME
            
            # Tag and push images
            docker tag disaster-response/backend:latest $REGISTRY/disaster-response/backend:latest
            docker tag disaster-response/frontend:latest $REGISTRY/disaster-response/frontend:latest
            docker push $REGISTRY/disaster-response/backend:latest
            docker push $REGISTRY/disaster-response/frontend:latest
            ;;
    esac
    
    log_info "Docker images built and pushed successfully"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    log_info "Deploying infrastructure with Terraform..."
    
    cd deployment/terraform
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan -var="cluster_name=$CLUSTER_NAME" -var="environment=$ENVIRONMENT"
    
    # Apply deployment
    terraform apply -var="cluster_name=$CLUSTER_NAME" -var="environment=$ENVIRONMENT" -auto-approve
    
    cd ../..
    
    log_info "Infrastructure deployed successfully"
}

# Configure kubectl
configure_kubectl() {
    log_info "Configuring kubectl..."
    
    case $CLOUD_PROVIDER in
        "aws")
            aws eks update-kubeconfig --region ${AWS_DEFAULT_REGION:-us-west-2} --name $CLUSTER_NAME
            ;;
        "gcp")
            gcloud container clusters get-credentials $CLUSTER_NAME --zone ${GCP_ZONE:-us-central1-a}
            ;;
        "azure")
            az aks get-credentials --resource-group ${AZURE_RESOURCE_GROUP:-disaster-response-rg} --name $CLUSTER_NAME
            ;;
    esac
    
    # Test kubectl connection
    kubectl cluster-info
    
    log_info "kubectl configured successfully"
}

# Deploy Kubernetes resources
deploy_kubernetes() {
    log_info "Deploying Kubernetes resources..."
    
    # Create namespace
    kubectl apply -f deployment/kubernetes/namespace.yaml
    
    # Apply ConfigMap
    kubectl apply -f deployment/kubernetes/configmap.yaml
    
    # Deploy backend
    kubectl apply -f deployment/kubernetes/backend-deployment.yaml
    
    # Deploy frontend
    kubectl apply -f deployment/kubernetes/frontend-deployment.yaml
    
    # Deploy ingress
    kubectl apply -f deployment/kubernetes/ingress.yaml
    
    # Wait for deployments to be ready
    log_info "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/disaster-response-backend -n $NAMESPACE
    kubectl wait --for=condition=available --timeout=300s deployment/disaster-response-frontend -n $NAMESPACE
    
    log_info "Kubernetes resources deployed successfully"
}

# Deploy monitoring stack
deploy_monitoring() {
    log_info "Deploying monitoring stack..."
    
    # Deploy Prometheus
    kubectl apply -f deployment/monitoring/prometheus.yaml
    
    # Deploy Grafana
    kubectl apply -f deployment/monitoring/grafana.yaml
    
    # Wait for monitoring services
    kubectl wait --for=condition=available --timeout=300s deployment/prometheus -n $NAMESPACE
    kubectl wait --for=condition=available --timeout=300s deployment/grafana -n $NAMESPACE
    
    log_info "Monitoring stack deployed successfully"
}

# Setup SSL certificates
setup_ssl() {
    log_info "Setting up SSL certificates..."
    
    # Install cert-manager if not present
    kubectl apply --validate=false -f https://github.com/jetstack/cert-manager/releases/download/v1.11.0/cert-manager.yaml
    
    # Wait for cert-manager
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager -n cert-manager-system
    
    log_info "SSL certificates configured"
}

# Get deployment information
get_deployment_info() {
    log_info "Getting deployment information..."
    
    echo "=================================="
    echo "Disaster Response System Deployed"
    echo "=================================="
    
    # Get service URLs
    echo "Services:"
    kubectl get services -n $NAMESPACE
    
    echo ""
    echo "Ingress:"
    kubectl get ingress -n $NAMESPACE
    
    echo ""
    echo "Pods:"
    kubectl get pods -n $NAMESPACE
    
    # Get LoadBalancer IPs
    FRONTEND_IP=$(kubectl get service disaster-response-frontend-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "Pending")
    GRAFANA_IP=$(kubectl get service grafana-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "Pending")
    
    echo ""
    echo "Access URLs (when LoadBalancers are ready):"
    echo "Frontend Dashboard: http://$FRONTEND_IP:8501"
    echo "Grafana Monitoring: http://$GRAFANA_IP:3000 (admin/admin123)"
    echo "API Endpoint: http://$FRONTEND_IP:8000"
    
    if [ "$FRONTEND_IP" = "Pending" ]; then
        log_warn "LoadBalancer IPs are still pending. Check again in a few minutes."
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up resources..."
    
    # Delete Kubernetes resources
    kubectl delete namespace $NAMESPACE --ignore-not-found=true
    
    # Destroy infrastructure
    cd deployment/terraform
    terraform destroy -var="cluster_name=$CLUSTER_NAME" -var="environment=$ENVIRONMENT" -auto-approve
    cd ../..
    
    log_info "Cleanup completed"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Check if all pods are running
    NOT_READY=$(kubectl get pods -n $NAMESPACE --field-selector=status.phase!=Running --no-headers 2>/dev/null | wc -l)
    
    if [ $NOT_READY -eq 0 ]; then
        log_info "All pods are running successfully"
        return 0
    else
        log_warn "$NOT_READY pods are not in Running state"
        kubectl get pods -n $NAMESPACE
        return 1
    fi
}

# Main deployment function
deploy() {
    log_info "Starting deployment of Disaster Response System..."
    log_info "Cloud Provider: $CLOUD_PROVIDER"
    log_info "Environment: $ENVIRONMENT"
    log_info "Cluster Name: $CLUSTER_NAME"
    
    check_prerequisites
    build_images
    deploy_infrastructure
    configure_kubectl
    deploy_kubernetes
    deploy_monitoring
    setup_ssl
    
    log_info "Deployment completed successfully!"
    
    # Wait a bit for services to stabilize
    sleep 30
    
    get_deployment_info
    health_check
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "cleanup")
        cleanup
        ;;
    "health")
        health_check
        ;;
    "info")
        get_deployment_info
        ;;
    *)
        echo "Usage: $0 {deploy|cleanup|health|info}"
        echo "  deploy  - Deploy the complete system"
        echo "  cleanup - Remove all resources"
        echo "  health  - Check system health"
        echo "  info    - Show deployment information"
        exit 1
        ;;
esac