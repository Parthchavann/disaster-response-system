"""
FastAPI Backend for Real-Time Disaster Response System
Provides REST APIs and WebSocket connections for real-time processing
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import asyncio
import json
import logging
from datetime import datetime, timedelta
import uuid
import redis
from kafka import KafkaConsumer
import threading
import base64
from PIL import Image
import io

# Import our custom modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ml_models.multimodal_fusion import DisasterMultimodalClassifier
from vector_search.vector_store import DisasterVectorStore
from feature_store.feature_engineering import DisasterFeatureEngineering
from auth.auth import get_current_user, require_permission, require_role, login, logout, refresh_access_token, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class DisasterEventRequest(BaseModel):
    text: Optional[str] = None
    image_data: Optional[str] = None  # Base64 encoded
    weather_data: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, float]] = None
    source: str = "api"
    metadata: Optional[Dict[str, Any]] = None

class DisasterEventResponse(BaseModel):
    event_id: str
    predictions: Dict[str, float]
    top_prediction: str
    confidence_score: float
    severity: str
    location: Optional[Dict[str, float]]
    timestamp: str
    processing_time_ms: float

class SearchRequest(BaseModel):
    query: str
    event_type: Optional[str] = None
    severity: Optional[str] = None
    location: Optional[Dict[str, float]] = None
    radius_km: Optional[float] = 50.0
    limit: int = 10

class AlertSubscription(BaseModel):
    location: Dict[str, float]
    radius_km: float = 50.0
    severity_threshold: str = "medium"
    event_types: Optional[List[str]] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Initialize FastAPI app
app = FastAPI(
    title="Disaster Response API",
    description="Real-time multimodal disaster detection and response system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global components
ml_classifier: Optional[DisasterMultimodalClassifier] = None
vector_store: Optional[DisasterVectorStore] = None
feature_engineer: Optional[DisasterFeatureEngineering] = None
redis_client: Optional[redis.Redis] = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[str, AlertSubscription] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client {client_id} connected")
    
    def disconnect(self, websocket: WebSocket, client_id: str):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
        logger.info(f"Client {client_id} disconnected")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(message))
    
    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)
    
    def add_subscription(self, client_id: str, subscription: AlertSubscription):
        self.subscriptions[client_id] = subscription
        logger.info(f"Added subscription for client {client_id}")

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global ml_classifier, vector_store, feature_engineer, redis_client
    
    try:
        # Initialize ML classifier
        logger.info("Initializing ML classifier...")
        ml_classifier = DisasterMultimodalClassifier()
        ml_classifier.initialize_models()
        
        # Initialize vector store
        logger.info("Initializing vector store...")
        vector_store = DisasterVectorStore()
        
        # Initialize feature engineer
        logger.info("Initializing feature engineer...")
        feature_engineer = DisasterFeatureEngineering()
        
        # Initialize Redis
        logger.info("Initializing Redis...")
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Start Kafka consumer in background
        threading.Thread(target=kafka_consumer_worker, daemon=True).start()
        
        logger.info("All components initialized successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if redis_client:
        redis_client.close()
    logger.info("Application shutdown complete")

def kafka_consumer_worker():
    """Background worker to consume Kafka messages and process them"""
    try:
        consumer = KafkaConsumer(
            'disaster.social.text',
            'disaster.social.images', 
            'disaster.weather.sensors',
            'disaster.satellite.data',
            bootstrap_servers=['localhost:9092'],
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        logger.info("Kafka consumer started")
        
        for message in consumer:
            try:
                event_data = message.value
                
                # Process the event
                asyncio.run(process_streaming_event(event_data))
                
            except Exception as e:
                logger.error(f"Error processing Kafka message: {e}")
                
    except Exception as e:
        logger.error(f"Kafka consumer error: {e}")

async def process_streaming_event(event_data: Dict[str, Any]):
    """Process streaming event and broadcast alerts if needed"""
    try:
        # Extract data based on source
        source_data = event_data.get('data', {})
        
        # Prepare request format
        request_data = {
            'location': event_data.get('location'),
            'source': event_data.get('source', 'stream'),
            'metadata': {
                'stream_timestamp': event_data.get('timestamp'),
                'event_id': event_data.get('event_id')
            }
        }
        
        if 'text' in source_data:
            request_data['text'] = source_data['text']
        
        if 'image_data' in source_data:
            request_data['image_data'] = source_data['image_data']
        
        if any(key in source_data for key in ['wind_speed_mph', 'precipitation_mm']):
            request_data['weather_data'] = source_data
        
        # Process the event
        result = await process_disaster_event_internal(request_data)
        
        # Check if this triggers any alert subscriptions
        await check_and_send_alerts(result)
        
        # Store in Redis for recent events cache
        if redis_client:
            redis_client.setex(
                f"recent_event:{result['event_id']}", 
                3600,  # 1 hour TTL
                json.dumps(result.dict())
            )
        
    except Exception as e:
        logger.error(f"Error processing streaming event: {e}")

async def check_and_send_alerts(event_result: DisasterEventResponse):
    """Check if event triggers any alert subscriptions"""
    
    severity_levels = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
    event_severity = severity_levels.get(event_result.severity, 0)
    
    for client_id, subscription in manager.subscriptions.items():
        try:
            # Check severity threshold
            threshold_level = severity_levels.get(subscription.severity_threshold, 0)
            if event_severity < threshold_level:
                continue
            
            # Check event type filter
            if subscription.event_types and event_result.top_prediction not in subscription.event_types:
                continue
            
            # Check location proximity
            if event_result.location and subscription.location:
                distance = calculate_distance(
                    event_result.location['lat'], event_result.location['lon'],
                    subscription.location['lat'], subscription.location['lon']
                )
                
                if distance > subscription.radius_km:
                    continue
            
            # Send alert
            alert_message = {
                'type': 'disaster_alert',
                'event': event_result.dict(),
                'subscription_id': client_id,
                'alert_reason': f"Event meets criteria: {event_result.top_prediction} with {event_result.severity} severity"
            }
            
            await manager.broadcast(alert_message)
            logger.info(f"Sent alert for event {event_result.event_id} to client {client_id}")
            
        except Exception as e:
            logger.error(f"Error checking alert subscription for {client_id}: {e}")

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km"""
    import math
    
    R = 6371  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat/2)**2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon/2)**2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

async def process_disaster_event_internal(event_data: Dict[str, Any]) -> DisasterEventResponse:
    """Internal function to process disaster events"""
    start_time = datetime.now()
    
    # Generate event ID
    event_id = str(uuid.uuid4())
    
    # Prepare data for ML models
    texts = [event_data['text']] if event_data.get('text') else None
    images = None
    
    if event_data.get('image_data'):
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(event_data['image_data'])
            image = Image.open(io.BytesIO(image_bytes))
            images = [image]
        except Exception as e:
            logger.error(f"Error decoding image: {e}")
    
    weather_data = [event_data['weather_data']] if event_data.get('weather_data') else None
    locations = [event_data['location']] if event_data.get('location') else None
    
    # Get multimodal prediction
    prediction_result = ml_classifier.predict_multimodal(
        texts=texts,
        images=images,
        weather_data=weather_data,
        locations=locations
    )
    
    # Determine severity based on prediction and confidence
    severity = determine_severity(prediction_result)
    
    # Create response
    response = DisasterEventResponse(
        event_id=event_id,
        predictions=prediction_result['predictions'],
        top_prediction=prediction_result['top_prediction'],
        confidence_score=prediction_result['top_score'],
        severity=severity,
        location=event_data.get('location'),
        timestamp=datetime.now().isoformat(),
        processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
    )
    
    # Index in vector store
    if vector_store:
        vector_event = {
            'event_id': event_id,
            'event_type': prediction_result['top_prediction'],
            'severity': severity,
            'confidence': prediction_result['top_score'],
            'text': event_data.get('text', ''),
            'location': event_data.get('location'),
            'source': event_data.get('source', 'api'),
            'timestamp': response.timestamp
        }
        vector_store.index_disaster_event(vector_event)
    
    return response

def determine_severity(prediction_result: Dict[str, Any]) -> str:
    """Determine severity based on prediction results"""
    confidence = prediction_result['top_score']
    prediction = prediction_result['top_prediction']
    
    # High confidence dangerous events
    if confidence > 0.8 and prediction in ['fire', 'hurricane', 'earthquake']:
        return 'critical'
    elif confidence > 0.7 and prediction in ['flood', 'tornado']:
        return 'high'
    elif confidence > 0.6 and prediction != 'no_disaster':
        return 'medium'
    else:
        return 'low'

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Disaster Response API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "predict": "/predict",
            "search": "/search", 
            "stats": "/stats",
            "health": "/health"
        }
    }

@app.post("/auth/login")
async def auth_login(request: LoginRequest):
    """User authentication endpoint"""
    try:
        return login(request.username, request.password)
    except Exception as e:
        logger.error(f"Error in login endpoint: {e}")
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/auth/logout")
async def auth_logout(current_user: User = Depends(get_current_user)):
    """User logout endpoint"""
    try:
        # Extract token from request headers would be done here
        return logout("")  # Token extraction logic needed
    except Exception as e:
        logger.error(f"Error in logout endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/refresh")
async def auth_refresh(request: RefreshTokenRequest):
    """Refresh access token endpoint"""
    try:
        return refresh_access_token(request.refresh_token)
    except Exception as e:
        logger.error(f"Error in refresh endpoint: {e}")
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/predict", response_model=DisasterEventResponse)
async def predict_disaster(
    request: DisasterEventRequest,
    current_user: User = Depends(require_permission("predict:disasters"))
):
    """Predict disaster from multimodal input"""
    try:
        result = await process_disaster_event_internal(request.dict())
        return result
        
    except Exception as e:
        logger.error(f"Error in predict endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_events(
    request: SearchRequest,
    current_user: User = Depends(require_permission("search:events"))
):
    """Search for similar disaster events"""
    try:
        if not vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")
        
        results = []
        
        # Text similarity search
        if request.query:
            similarity_results = vector_store.search_similar_events(
                query_text=request.query,
                event_type=request.event_type,
                severity=request.severity,
                limit=request.limit
            )
            results.extend(similarity_results)
        
        # Location-based search
        if request.location:
            location_results = vector_store.search_by_location(
                lat=request.location['lat'],
                lon=request.location['lon'],
                radius_km=request.radius_km,
                limit=request.limit
            )
            results.extend(location_results)
        
        return {
            "query": request.query,
            "total_results": len(results),
            "results": results[:request.limit]
        }
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/{event_id}")
async def get_event(event_id: str):
    """Get specific event by ID"""
    try:
        if not vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")
        
        event = vector_store.get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return event
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_statistics(current_user: User = Depends(require_permission("view:stats"))):
    """Get system statistics"""
    try:
        stats = {
            "system_status": "operational",
            "timestamp": datetime.now().isoformat(),
            "active_connections": len(manager.active_connections),
            "active_subscriptions": len(manager.subscriptions)
        }
        
        # Add vector store stats if available
        if vector_store:
            vector_stats = vector_store.get_event_statistics()
            stats.update(vector_stats)
        
        # Add Redis stats if available
        if redis_client:
            try:
                redis_info = redis_client.info()
                stats["redis"] = {
                    "connected_clients": redis_info.get("connected_clients", 0),
                    "used_memory_human": redis_info.get("used_memory_human", "0B")
                }
            except Exception as e:
                logger.error(f"Error getting Redis stats: {e}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # Check ML classifier
    health_status["components"]["ml_classifier"] = "healthy" if ml_classifier else "unhealthy"
    
    # Check vector store
    try:
        if vector_store:
            vector_store.get_event_statistics()
            health_status["components"]["vector_store"] = "healthy"
        else:
            health_status["components"]["vector_store"] = "unhealthy"
    except Exception:
        health_status["components"]["vector_store"] = "unhealthy"
    
    # Check Redis
    try:
        if redis_client:
            redis_client.ping()
            health_status["components"]["redis"] = "healthy"
        else:
            health_status["components"]["redis"] = "unhealthy"
    except Exception:
        health_status["components"]["redis"] = "unhealthy"
    
    # Overall status
    unhealthy_components = [k for k, v in health_status["components"].items() if v == "unhealthy"]
    if unhealthy_components:
        health_status["status"] = "degraded"
        health_status["unhealthy_components"] = unhealthy_components
    
    return health_status

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time alerts"""
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Wait for client messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "subscribe_alerts":
                # Subscribe to disaster alerts
                subscription_data = message.get("subscription", {})
                subscription = AlertSubscription(**subscription_data)
                manager.add_subscription(client_id, subscription)
                
                await manager.send_personal_message(
                    {"type": "subscription_confirmed", "client_id": client_id},
                    websocket
                )
            
            elif message.get("type") == "ping":
                # Respond to ping
                await manager.send_personal_message(
                    {"type": "pong", "timestamp": datetime.now().isoformat()},
                    websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(websocket, client_id)

@app.get("/recent-events")
async def get_recent_events(limit: int = 20):
    """Get recent events from Redis cache"""
    try:
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis not available")
        
        # Get recent event keys
        keys = redis_client.keys("recent_event:*")
        events = []
        
        for key in keys[-limit:]:  # Get most recent
            event_data = redis_client.get(key)
            if event_data:
                events.append(json.loads(event_data))
        
        return {
            "total": len(events),
            "events": sorted(events, key=lambda x: x['timestamp'], reverse=True)
        }
        
    except Exception as e:
        logger.error(f"Error getting recent events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)