# 🔮 NEXUS Deployment Guide

**Real-Time Multimodal Disaster Intelligence System**

This guide provides comprehensive instructions for deploying NEXUS in various environments.

## 🚀 Quick Start (Local Deployment)

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 10GB+ disk space

### One-Click Deployment
```bash
# Clone the repository
git clone https://github.com/Parthchavann/disaster-response-system.git
cd disaster-response-system

# Deploy NEXUS
./deploy.sh
```

**Dashboard Access**: http://localhost:8503

## 📋 Deployment Options

### 1. Docker Compose (Recommended for Development/Staging)

```bash
# Build and start services
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Stop services
docker-compose -f docker-compose.production.yml down
```

### 2. Standalone Docker

```bash
# Build image
docker build -f Dockerfile.nexus -t nexus-intelligence:latest .

# Run container
docker run -d \
  --name nexus-production \
  -p 8503:8503 \
  --env-file .env.production \
  nexus-intelligence:latest

# Check health
curl http://localhost:8503/api/live-data
```

### 3. Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f kubernetes/nexus-deployment.yaml

# Check deployment status
kubectl get pods -n nexus-system
kubectl get services -n nexus-system

# Port forward for local access
kubectl port-forward -n nexus-system service/nexus-dashboard-service 8503:8503
```

### 4. Cloud Platform Deployment

#### AWS ECS
```bash
# Build and push to ECR
aws ecr create-repository --repository-name nexus-intelligence
docker tag nexus-intelligence:latest <account-id>.dkr.ecr.<region>.amazonaws.com/nexus-intelligence:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/nexus-intelligence:latest

# Deploy using ECS task definition (see aws-ecs-task.json)
aws ecs create-service --cluster nexus-cluster --service-name nexus-dashboard --task-definition nexus-task
```

#### Google Cloud Run
```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT-ID/nexus-intelligence

# Deploy to Cloud Run
gcloud run deploy nexus-dashboard \
  --image gcr.io/PROJECT-ID/nexus-intelligence \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8503
```

#### Azure Container Instances
```bash
# Create resource group
az group create --name nexus-rg --location eastus

# Deploy container
az container create \
  --resource-group nexus-rg \
  --name nexus-dashboard \
  --image nexus-intelligence:latest \
  --ports 8503 \
  --dns-name-label nexus-intelligence \
  --environment-variables NODE_ENV=production
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_ENV` | `production` | Environment mode |
| `PORT` | `8503` | Server port |
| `HOST` | `0.0.0.0` | Server host |
| `API_BASE_URL` | `http://localhost:9999` | Backend API URL |
| `DASHBOARD_UPDATE_INTERVAL` | `5000` | Update interval (ms) |
| `ENABLE_LIVE_DATA` | `true` | Enable live data updates |
| `ENABLE_MOCK_DATA` | `true` | Enable mock data generation |
| `LOG_LEVEL` | `INFO` | Logging level |

### Production Configuration

1. **Update Environment File**:
   ```bash
   cp .env.production .env.local
   # Edit .env.local with your specific settings
   ```

2. **SSL/TLS Setup**:
   ```bash
   # Place SSL certificates in nginx/ssl/
   cp your-cert.crt nginx/ssl/
   cp your-key.key nginx/ssl/
   ```

3. **Domain Configuration**:
   - Update `nginx/nginx.conf` with your domain name
   - Configure DNS to point to your server
   - Update Kubernetes ingress with your domain

## 🔍 Monitoring & Health Checks

### Health Endpoints
- **Live Data**: `GET /api/live-data`
- **System Health**: `GET /health`
- **Prediction API**: `POST /api/predict`

### Monitoring Stack
```bash
# Start with monitoring
docker-compose -f docker-compose.production.yml --profile monitoring up -d

# Access monitoring
# Grafana: http://localhost:3000 (admin/admin123)
# Prometheus: http://localhost:9090
```

### Log Management
```bash
# View application logs
docker logs nexus-production -f

# View nginx logs
docker logs nexus-proxy -f

# Kubernetes logs
kubectl logs -f -n nexus-system deployment/nexus-dashboard
```

## 🛡️ Security Configuration

### Production Security Checklist
- [ ] Change default secret keys in `.env.production`
- [ ] Enable SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Set up rate limiting
- [ ] Enable security headers
- [ ] Configure CORS origins
- [ ] Set up monitoring alerts

### Firewall Rules
```bash
# Allow HTTP/HTTPS traffic
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8503/tcp  # NEXUS dashboard
sudo ufw enable
```

### SSL Certificate Setup (Let's Encrypt)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d nexus.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 🔧 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Find and kill process
   lsof -ti:8503 | xargs -r kill -9
   ```

2. **Container Won't Start**
   ```bash
   # Check logs
   docker logs nexus-production
   
   # Check resources
   docker stats
   ```

3. **Health Check Failing**
   ```bash
   # Test manually
   curl -f http://localhost:8503/api/live-data
   
   # Check network connectivity
   docker exec nexus-production netstat -tlnp
   ```

4. **Performance Issues**
   ```bash
   # Monitor resources
   docker stats nexus-production
   
   # Scale horizontally (Docker Swarm/Kubernetes)
   kubectl scale deployment nexus-dashboard --replicas=5 -n nexus-system
   ```

## 📈 Scaling & Performance

### Horizontal Scaling
```bash
# Docker Swarm
docker service scale nexus-stack_nexus-dashboard=3

# Kubernetes
kubectl scale deployment nexus-dashboard --replicas=3 -n nexus-system
```

### Load Balancing
- Nginx (included in docker-compose)
- Kubernetes Ingress Controller
- Cloud Load Balancers (ALB, GCP Load Balancer, Azure Load Balancer)

### Performance Tuning
```bash
# Increase container resources
docker run --memory="1g" --cpus="1.0" nexus-intelligence:latest

# Enable caching
export CACHE_ENABLED=true
export REDIS_HOST=redis-server
```

## 🔄 CI/CD Pipeline

### GitHub Actions Example
```yaml
name: Deploy NEXUS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build and Deploy
        run: |
          docker build -f Dockerfile.nexus -t nexus-intelligence:latest .
          ./deploy.sh
```

### Automated Deployment
```bash
# Set up webhook for auto-deployment
curl -X POST http://your-server/webhook \
  -H "Content-Type: application/json" \
  -d '{"ref": "refs/heads/main", "repository": {"clone_url": "https://github.com/Parthchavann/disaster-response-system.git"}}'
```

## 📞 Support

### Getting Help
- **Documentation**: [CLAUDE.md](./CLAUDE.md)
- **Issues**: [GitHub Issues](https://github.com/Parthchavann/disaster-response-system/issues)
- **Logs**: Check container logs and health endpoints

### Deployment Script Commands
```bash
./deploy.sh help     # Show all available commands
./deploy.sh deploy   # Full deployment
./deploy.sh start    # Start services
./deploy.sh stop     # Stop services
./deploy.sh restart  # Restart services
./deploy.sh logs     # View live logs
./deploy.sh status   # Show status
./deploy.sh clean    # Clean up deployment
```

---

🔮 **NEXUS: Real-Time Multimodal Disaster Intelligence System**
*Powered by Advanced AI Analytics for Global Disaster Response*