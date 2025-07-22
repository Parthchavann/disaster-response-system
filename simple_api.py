#!/usr/bin/env python3
"""
Simplified API server for the disaster response system demo.
Runs without heavy ML dependencies using mock models.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import hashlib
from datetime import datetime
import random
import uvicorn

# Import our demo models
from simple_demo import MockDisasterClassifier, MockVectorStore, DisasterEvent, DisasterResponseDemo

# Pydantic models for API
class DisasterEventRequest(BaseModel):
    text: Optional[str] = None
    location: Optional[Dict[str, float]] = None
    source: str = "api"

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
    limit: int = 10

# Initialize FastAPI app
app = FastAPI(
    title="Disaster Response API - Demo",
    description="Simplified disaster response system for demonstration",
    version="1.0.0-demo"
)

# Global demo system
demo_system = DisasterResponseDemo()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Disaster Response API - Demo Mode",
        "version": "1.0.0-demo",
        "status": "operational",
        "note": "This is a simplified demo without heavy ML dependencies",
        "endpoints": {
            "predict": "/predict",
            "search": "/search",
            "stats": "/stats",
            "health": "/health",
            "events": "/events"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "ml_classifier": "healthy (mock)",
            "vector_store": "healthy (mock)", 
            "demo_mode": True
        },
        "system_info": {
            "events_processed": demo_system.processed_events,
            "total_stored_events": len(demo_system.vector_store.events)
        }
    }

@app.post("/predict", response_model=DisasterEventResponse)
async def predict_disaster(request: DisasterEventRequest):
    """Predict disaster from input text"""
    try:
        start_time = datetime.now()
        
        if not request.text:
            raise HTTPException(status_code=400, detail="Text is required for prediction")
        
        # Process the event using our demo system
        event = demo_system.process_event(
            text=request.text,
            location=request.location
        )
        
        # Get detailed predictions
        result = demo_system.classifier.predict(request.text)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        response = DisasterEventResponse(
            event_id=event.event_id,
            predictions=result["predictions"],
            top_prediction=event.prediction,
            confidence_score=event.confidence,
            severity=event.severity,
            location=request.location,
            timestamp=event.timestamp,
            processing_time_ms=processing_time
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@app.post("/search")
async def search_events(request: SearchRequest):
    """Search for similar disaster events"""
    try:
        results = demo_system.vector_store.search_similar(
            query=request.query,
            limit=request.limit
        )
        
        formatted_results = []
        for result in results:
            event = result["event"]
            formatted_results.append({
                "id": event.event_id,
                "text": event.text,
                "disaster_type": event.prediction,
                "confidence": event.confidence,
                "severity": event.severity,
                "location": event.location,
                "timestamp": event.timestamp,
                "score": result["score"]
            })
        
        return {
            "query": request.query,
            "total_results": len(formatted_results),
            "results": formatted_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.get("/stats")
async def get_statistics():
    """Get system statistics"""
    try:
        stats = demo_system.vector_store.get_stats()
        
        return {
            "system_status": "operational (demo mode)",
            "timestamp": datetime.now().isoformat(),
            "total_events": stats["total_events"],
            "events_processed": demo_system.processed_events,
            "disaster_type_distribution": stats["disaster_distribution"],
            "last_updated": stats["last_updated"],
            "demo_mode": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")

@app.get("/events")
async def get_recent_events(limit: int = 20):
    """Get recent events"""
    try:
        events = demo_system.vector_store.events[-limit:]
        
        formatted_events = []
        for event in reversed(events):  # Most recent first
            formatted_events.append({
                "event_id": event.event_id,
                "text": event.text,
                "disaster_type": event.prediction,
                "confidence": event.confidence,
                "severity": event.severity,
                "location": event.location,
                "timestamp": event.timestamp,
                "source": event.source
            })
        
        return {
            "total": len(formatted_events),
            "events": formatted_events
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Events error: {str(e)}")

@app.get("/events/{event_id}")
async def get_event(event_id: str):
    """Get specific event by ID"""
    try:
        for event in demo_system.vector_store.events:
            if event.event_id == event_id:
                return {
                    "id": event.event_id,
                    "text": event.text,
                    "disaster_type": event.prediction,
                    "confidence": event.confidence,
                    "severity": event.severity,
                    "location": event.location,
                    "timestamp": event.timestamp,
                    "source": event.source
                }
        
        raise HTTPException(status_code=404, detail="Event not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event retrieval error: {str(e)}")

@app.post("/demo/load-sample-data")
async def load_sample_data():
    """Load sample disaster events for demonstration"""
    try:
        sample_events = [
            {
                "text": "URGENT: Flash flood warning issued for downtown area. Water levels rising rapidly!",
                "location": {"latitude": 40.7128, "longitude": -74.0060}
            },
            {
                "text": "Wildfire spreading rapidly near residential areas. Evacuation orders in effect.",
                "location": {"latitude": 34.0522, "longitude": -118.2437}
            },
            {
                "text": "Earthquake magnitude 6.2 detected. Buildings shaking, people evacuating.",
                "location": {"latitude": 37.7749, "longitude": -122.4194}
            },
            {
                "text": "Hurricane Category 3 approaching coastline. Storm surge warning issued.",
                "location": {"latitude": 25.7617, "longitude": -80.1918}
            },
            {
                "text": "Tornado sighted moving northeast at 45 mph. Take cover immediately!",
                "location": {"latitude": 35.2271, "longitude": -101.8313}
            },
            {
                "text": "Landslide blocking major highway. Emergency crews responding.",
                "location": {"latitude": 47.6062, "longitude": -122.3321}
            },
            {
                "text": "Severe thunderstorm with hail reported. Power outages in multiple areas.",
                "location": {"latitude": 39.7392, "longitude": -104.9903}
            },
            {
                "text": "Beautiful sunny day at the beach. Perfect weather for outdoor activities.",
                "location": {"latitude": 33.7490, "longitude": -84.3880}
            }
        ]
        
        events_created = []
        for event_data in sample_events:
            event = demo_system.process_event(
                text=event_data["text"],
                location=event_data.get("location")
            )
            events_created.append(event.event_id)
        
        return {
            "message": f"Successfully loaded {len(events_created)} sample events",
            "event_ids": events_created,
            "total_events_now": len(demo_system.vector_store.events)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sample data loading error: {str(e)}")

if __name__ == "__main__":
    print("🚨 Starting Disaster Response API Demo Server...")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔗 Interactive API: http://localhost:8000/redoc")
    print("💡 Load sample data: POST http://localhost:8000/demo/load-sample-data")
    print("=" * 60)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )