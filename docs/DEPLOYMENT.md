# Deployment Guide

## Overview

This guide covers deployment options for the Disaster Response System, from local development to production cloud deployments.

## Prerequisites

- Docker & Docker Compose
- Kubernetes cluster (for production)
- Cloud provider account (AWS/GCP/Azure)
- Domain name and SSL certificates (production)

## Local Development Deployment

### 1. Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd disaster-response-system

# Copy environment configuration
cp configs/development.env .env

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Start Infrastructure Services

```bash
# Start all services with Docker Compose
docker-compose up -d

# Verify services are running
docker-compose ps
```

Expected services:
- **Kafka**: Port 9092
- **Zookeeper**: Port 2181
- **Redis**: Port 6379
- **Qdrant**: Port 6333
- **MLflow**: Port 5000
- **Prometheus**: Port 9090
- **Grafana**: Port 3000

### 3. Initialize ML Models

```bash
# Train and save ML models
python train_models.py

# Verify models are saved
ls trained_models/
```

### 4. Start Application Services

```bash
# Start data ingestion
python data-ingestion/kafka_producer.py &

# Start stream processing
python data-ingestion/spark_streaming.py &

# Start backend API
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (in another terminal)
cd frontend
streamlit run app.py --server.port 8501
```

### 5. Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Frontend access
open http://localhost:8501
```

## Production Deployment

### Option 1: Kubernetes Deployment

#### 1. Prepare Configuration

```bash
# Copy production environment
cp configs/production.env .env

# Update secrets in the file
vim .env
```

**Critical secrets to update:**
- `JWT_SECRET_KEY`
- `REDIS_PASSWORD`
- `QDRANT_API_KEY`
- `KAFKA_SASL_PASSWORD`
- API keys for external services

#### 2. Build Docker Images

```bash
# Build backend image
docker build -t disaster-response-backend:latest .

# Build frontend image
docker build -f frontend/Dockerfile -t disaster-response-frontend:latest frontend/

# Tag for registry
docker tag disaster-response-backend:latest your-registry/disaster-response-backend:v1.0.0
docker tag disaster-response-frontend:latest your-registry/disaster-response-frontend:v1.0.0

# Push to registry
docker push your-registry/disaster-response-backend:v1.0.0
docker push your-registry/disaster-response-frontend:v1.0.0
```

#### 3. Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f deployment/kubernetes/namespace.yaml

# Deploy ConfigMap
kubectl apply -f deployment/kubernetes/configmap.yaml

# Deploy applications
kubectl apply -f deployment/kubernetes/backend-deployment.yaml
kubectl apply -f deployment/kubernetes/frontend-deployment.yaml

# Deploy ingress
kubectl apply -f deployment/kubernetes/ingress.yaml

# Deploy monitoring
kubectl apply -f deployment/monitoring/prometheus.yaml
kubectl apply -f deployment/monitoring/grafana.yaml
```

#### 4. Verify Kubernetes Deployment

```bash
# Check pods
kubectl get pods -n disaster-response

# Check services
kubectl get services -n disaster-response

# Check ingress
kubectl get ingress -n disaster-response

# View logs
kubectl logs -f deployment/backend -n disaster-response
```

### Option 2: Cloud Provider Deployment

#### Using Terraform (Automated)

```bash
# Initialize Terraform
cd deployment/terraform
terraform init

# Plan deployment
terraform plan -var="environment=production"

# Apply deployment
terraform apply -var="environment=production"
```

#### Manual Cloud Setup

##### AWS Deployment

```bash
# Set environment
export CLOUD_PROVIDER=aws
export AWS_REGION=us-east-1

# Create EKS cluster
eksctl create cluster --name disaster-response --region us-east-1 --nodes 3

# Deploy application
./deployment/deploy.sh deploy
```

##### GCP Deployment

```bash
# Set environment
export CLOUD_PROVIDER=gcp
export GCP_PROJECT=your-project-id

# Create GKE cluster
gcloud container clusters create disaster-response \
  --zone us-central1-a \
  --num-nodes 3

# Deploy application
./deployment/deploy.sh deploy
```

##### Azure Deployment

```bash
# Set environment
export CLOUD_PROVIDER=azure
export AZURE_RESOURCE_GROUP=disaster-response-rg

# Create AKS cluster
az aks create \
  --resource-group disaster-response-rg \
  --name disaster-response \
  --node-count 3

# Deploy application
./deployment/deploy.sh deploy
```

## Environment-Specific Configurations

### Development
- Single replicas
- Mock data sources
- Debug logging enabled
- Local storage

### Staging
- 2 replicas
- Real data sources (limited)
- Info logging
- Cloud storage

### Production
- 3+ replicas
- All data sources enabled
- Warning/Error logging
- High availability setup

## Database Setup

### Redis Configuration

```yaml
# redis-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-config
data:
  redis.conf: |
    maxmemory 2gb
    maxmemory-policy allkeys-lru
    save 900 1
    save 300 10
    save 60 10000
```

### Qdrant Configuration

```yaml
# qdrant-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: qdrant-config
data:
  config.yaml: |
    service:
      host: 0.0.0.0
      http_port: 6333
      grpc_port: 6334
    storage:
      storage_path: /qdrant/storage
```

## Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'disaster-response-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: /metrics

  - job_name: 'disaster-response-frontend'
    static_configs:
      - targets: ['frontend:8501']
```

### Grafana Dashboards

Import dashboards for:
- API performance metrics
- ML model performance
- System resource usage
- Alert statistics

## Security Configuration

### TLS/SSL Setup

```bash
# Generate certificates with Let's Encrypt
certbot certonly --nginx -d api.disaster-response.com -d dashboard.disaster-response.com

# Create Kubernetes secret
kubectl create secret tls disaster-response-tls \
  --cert=/etc/letsencrypt/live/api.disaster-response.com/fullchain.pem \
  --key=/etc/letsencrypt/live/api.disaster-response.com/privkey.pem \
  -n disaster-response
```

### Network Security

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: disaster-response-netpol
spec:
  podSelector:
    matchLabels:
      app: disaster-response
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: disaster-response
    ports:
    - protocol: TCP
      port: 8000
```

## Scaling Configuration

### Horizontal Pod Autoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Vertical Pod Autoscaler

```yaml
# vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: backend-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  updatePolicy:
    updateMode: "Auto"
```

## Backup and Recovery

### Database Backup

```bash
# Redis backup
kubectl exec redis-pod -- redis-cli BGSAVE

# Qdrant backup
kubectl exec qdrant-pod -- tar -czf /backup/qdrant-backup.tar.gz /qdrant/storage
```

### Application Backup

```bash
# Backup ML models
kubectl cp backend-pod:/app/trained_models ./backup/models/

# Backup configuration
kubectl get configmap disaster-response-config -o yaml > backup/config.yaml
```

## Health Checks and Monitoring

### Application Health Checks

```yaml
# In deployment.yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Custom Alerts

```yaml
# alertmanager.yml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'disaster-response-alerts'

receivers:
- name: 'disaster-response-alerts'
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    channel: '#disaster-alerts'
    title: 'Disaster Response System Alert'
```

## Troubleshooting

### Common Issues

1. **Pod not starting**
```bash
kubectl describe pod <pod-name> -n disaster-response
kubectl logs <pod-name> -n disaster-response
```

2. **Service not accessible**
```bash
kubectl get endpoints -n disaster-response
kubectl port-forward service/backend 8000:8000 -n disaster-response
```

3. **Database connection issues**
```bash
kubectl exec -it backend-pod -- python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"
```

4. **ML model loading errors**
```bash
kubectl exec -it backend-pod -- ls -la /app/trained_models/
```

### Performance Tuning

1. **Increase worker processes**
```yaml
env:
- name: API_WORKERS
  value: "4"
```

2. **Tune memory limits**
```yaml
resources:
  limits:
    memory: "4Gi"
    cpu: "2"
  requests:
    memory: "2Gi"
    cpu: "1"
```

3. **Enable caching**
```yaml
env:
- name: CACHE_TTL
  value: "1800"
```

## Maintenance

### Rolling Updates

```bash
# Update image
kubectl set image deployment/backend backend=disaster-response-backend:v1.1.0 -n disaster-response

# Check rollout status
kubectl rollout status deployment/backend -n disaster-response

# Rollback if needed
kubectl rollout undo deployment/backend -n disaster-response
```

### Regular Maintenance Tasks

1. **Update dependencies** (monthly)
2. **Rotate secrets** (quarterly)
3. **Update ML models** (as needed)
4. **Review logs** (weekly)
5. **Performance analysis** (monthly)

## Cost Optimization

### Resource Right-sizing

```bash
# Analyze resource usage
kubectl top pods -n disaster-response
kubectl top nodes

# Adjust resource requests/limits based on usage
```

### Auto-scaling Policies

```yaml
# Scale down during low-traffic periods
- type: Pods
  value: 1
  periodSeconds: 300
```

This deployment guide ensures a robust, scalable, and secure deployment of the Disaster Response System across different environments.