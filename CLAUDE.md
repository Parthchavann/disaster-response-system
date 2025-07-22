# Real-Time Multimodal Disaster Response System - Setup Guide

## Project Overview

This is a comprehensive real-time disaster response system that processes multimodal data streams (text, images, videos, weather sensors, satellite feeds) to automatically detect, classify, and map disaster events.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Data Ingestion │    │   ML Processing  │    │   Frontend      │
│  (Kafka/Spark)  │───▶│   (PyTorch/HF)   │───▶│  (Streamlit)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Vector Search  │    │  Feature Store   │    │    Backend      │
│  (Qdrant/FAISS)│    │  (Feast/TFX)     │    │   (FastAPI)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              GenAI/RAG (LangChain) + MLOps (MLflow)             │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Kubernetes (optional)
- Cloud CLI (AWS/GCP/Azure)

### Local Development Setup

1. **Clone and Install Dependencies**
```bash
cd disaster-response-system
pip install -r requirements.txt
```

2. **Start Infrastructure Services**
```bash
docker-compose up -d
```

3. **Initialize Models and Data**
```bash
# Train initial models
python ml-models/text_classifier.py
python ml-models/image_classifier.py

# Start data ingestion
python data-ingestion/kafka_producer.py &

# Start stream processing
python data-ingestion/spark_streaming.py &
```

4. **Launch Backend API**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

5. **Launch Frontend Dashboard**
```bash
cd frontend
streamlit run app.py --server.port 8501
```

### Production Deployment

```bash
# Set environment variables
export CLOUD_PROVIDER=aws  # or gcp, azure
export ENVIRONMENT=production

# Deploy to cloud
chmod +x deployment/deploy.sh
./deployment/deploy.sh deploy
```

## Project Structure

```
disaster-response-system/
├── data-ingestion/          # Kafka producers and Spark streaming
├── ml-models/              # Multimodal ML models (text, image, fusion)
├── feature-store/          # Feature engineering and Feast integration
├── vector-search/          # Qdrant vector database and search
├── backend/               # FastAPI REST API and WebSocket server
├── frontend/              # Streamlit dashboard and visualization
├── mlops/                 # MLflow experiment tracking and model registry
├── genai/                 # LangChain RAG system for intelligent reporting
├── deployment/            # Kubernetes manifests, Terraform, deployment scripts
├── monitoring/            # Prometheus, Grafana, custom alerting
└── configs/               # Configuration files
```

## API Endpoints

- **Health Check**: `GET /health`
- **Predict Disaster**: `POST /predict`
- **Search Events**: `POST /search`
- **Get Event**: `GET /events/{event_id}`
- **Statistics**: `GET /stats`
- **Recent Events**: `GET /recent-events`
- **WebSocket Alerts**: `WS /ws/{client_id}`

## Dashboard Features

- 🗺️ Real-time disaster event mapping
- 📊 Event analytics and trends
- 🔍 Multimodal prediction interface
- 🔎 Event search and similarity analysis
- ⚙️ System monitoring and configuration

## Environment Variables

```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPICS=disaster.social.text,disaster.social.images,disaster.weather.sensors,disaster.satellite.data

# Database Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
QDRANT_HOST=localhost
QDRANT_PORT=6333

# MLflow Configuration
MLFLOW_TRACKING_URI=sqlite:///mlruns.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# OpenAI (optional for GenAI features)
OPENAI_API_KEY=your_api_key_here
```

## Testing

```bash
# Run unit tests
pytest tests/

# Test data ingestion
python data-ingestion/kafka_producer.py

# Test ML models
python ml-models/text_classifier.py
python ml-models/image_classifier.py

# Test API
curl http://localhost:8000/health

# Load test
python tests/load_test.py
```

## Monitoring & Alerting

- **Prometheus**: Metrics collection at `:9090`
- **Grafana**: Dashboards at `:3000` (admin/admin123)
- **Custom Alerts**: Email, Slack, SMS notifications
- **Health Checks**: Automated system monitoring

## Scaling & Performance

- **Horizontal Scaling**: Kubernetes auto-scaling
- **Caching**: Redis for real-time data
- **Database**: Qdrant for vector similarity search
- **CDN**: CloudFront for static assets
- **Load Balancing**: Application Load Balancer

## Security

- **Authentication**: JWT tokens
- **Authorization**: Role-based access control
- **Encryption**: TLS/SSL for all communications
- **Secrets**: Kubernetes secrets management
- **Network**: VPC with security groups

## Disaster Categories

The system detects and classifies:
- 🌊 Floods
- 🔥 Wildfires
- 🌪️ Tornadoes
- 🌀 Hurricanes
- 🌍 Earthquakes
- ❄️ Winter Storms
- 🏔️ Other Natural Disasters

## Data Sources

- **Social Media**: Twitter, Facebook, Instagram posts
- **Weather Sensors**: Temperature, wind, pressure, precipitation
- **Satellite Images**: Thermal, optical, radar imagery
- **News Feeds**: Emergency broadcasts and news articles
- **Government APIs**: USGS, NOAA, emergency services

## ML Models

1. **Text Classifier**: DistilBERT for disaster text classification
2. **Image Classifier**: ResNet-50/ViT for disaster image analysis
3. **Multimodal Fusion**: Attention-based fusion of text, image, weather, and geo features
4. **Time Series**: Prophet for trend analysis
5. **Anomaly Detection**: Isolation Forest for outlier detection

## Integration APIs

- **Emergency Services**: CAP alerts, emergency broadcasts
- **Weather APIs**: OpenWeatherMap, NOAA
- **Social Media**: Twitter API, Reddit API
- **Mapping**: Google Maps, OpenStreetMap
- **Cloud Services**: AWS Bedrock, GCP Vertex AI, Azure Cognitive Services

## Development Commands

```bash
# Format code
black .
flake8 .

# Type checking
mypy .

# Security scan
bandit -r .

# Documentation
sphinx-build docs/ docs/_build/

# Package building
python setup.py sdist bdist_wheel
```

## Troubleshooting

### Common Issues

1. **Kafka Connection Failed**
   - Check if Kafka is running: `docker ps`
   - Verify bootstrap servers: `KAFKA_BOOTSTRAP_SERVERS`

2. **Model Loading Errors**
   - Ensure models are trained: `python ml-models/text_classifier.py`
   - Check model file permissions

3. **Database Connection Issues**
   - Verify Redis: `redis-cli ping`
   - Check Qdrant: `curl http://localhost:6333/collections`

4. **High Memory Usage**
   - Reduce batch sizes in ML models
   - Implement model quantization
   - Use model checkpointing

### Performance Optimization

- Enable GPU acceleration for ML models
- Use model caching and preloading
- Implement connection pooling
- Configure appropriate resource limits

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -m 'Add new feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Submit pull request

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Support

- **Documentation**: https://docs.disaster-response.com
- **Issues**: GitHub Issues
- **Community**: Discord Server
- **Email**: support@disaster-response.com

---

🚨 **This system is designed to save lives by enabling faster disaster response through real-time multimodal AI analysis.**