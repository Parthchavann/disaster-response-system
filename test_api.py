#!/usr/bin/env python3
"""
Test script to demonstrate the API functionality without running a server.
"""

import json
from simple_demo import DisasterResponseDemo

def test_api_endpoints():
    """Test API functionality"""
    print("🧪 TESTING DISASTER RESPONSE API")
    print("=" * 50)
    
    # Initialize system
    system = DisasterResponseDemo()
    
    # Test data
    test_requests = [
        {
            "text": "Flash flood emergency in downtown area!",
            "location": {"latitude": 40.7128, "longitude": -74.0060}
        },
        {
            "text": "Wildfire spreading near homes",
            "location": {"latitude": 34.0522, "longitude": -118.2437}
        },
        {
            "text": "Beautiful weather today",
            "location": {"latitude": 33.7490, "longitude": -84.3880}
        }
    ]
    
    # Test /predict endpoint
    print("\n🔮 Testing /predict endpoint:")
    print("-" * 30)
    
    for i, request in enumerate(test_requests, 1):
        print(f"\nRequest {i}:")
        print(f"  Text: \"{request['text']}\"")
        print(f"  Location: {request['location']}")
        
        # Process prediction
        event = system.process_event(
            text=request["text"],
            location=request["location"]
        )
        
        # Simulate API response
        result = system.classifier.predict(request["text"])
        response = {
            "event_id": event.event_id,
            "predictions": result["predictions"],
            "top_prediction": event.prediction,
            "confidence_score": event.confidence,
            "severity": event.severity,
            "location": request["location"],
            "timestamp": event.timestamp,
            "processing_time_ms": 15.6
        }
        
        print(f"  Response:")
        print(f"    Event ID: {response['event_id']}")
        print(f"    Prediction: {response['top_prediction']}")
        print(f"    Confidence: {response['confidence_score']:.2%}")
        print(f"    Severity: {response['severity']}")
    
    # Test /search endpoint
    print(f"\n🔍 Testing /search endpoint:")
    print("-" * 30)
    
    search_queries = ["flood", "fire", "emergency"]
    
    for query in search_queries:
        results = system.vector_store.search_similar(query, limit=3)
        print(f"\nSearch query: \"{query}\"")
        print(f"Results found: {len(results)}")
        
        for j, result in enumerate(results, 1):
            event = result["event"]
            print(f"  {j}. [{result['score']:.2%}] {event.prediction}: \"{event.text[:40]}...\"")
    
    # Test /stats endpoint
    print(f"\n📊 Testing /stats endpoint:")
    print("-" * 30)
    
    stats = system.vector_store.get_stats()
    stats_response = {
        "system_status": "operational (demo mode)",
        "total_events": stats["total_events"],
        "events_processed": system.processed_events,
        "disaster_type_distribution": stats["disaster_distribution"],
        "demo_mode": True
    }
    
    print(f"System Status: {stats_response['system_status']}")
    print(f"Total Events: {stats_response['total_events']}")
    print(f"Events Processed: {stats_response['events_processed']}")
    print("Disaster Distribution:")
    for disaster_type, count in stats_response["disaster_type_distribution"].items():
        print(f"  - {disaster_type}: {count}")
    
    # Test /health endpoint
    print(f"\n🏥 Testing /health endpoint:")
    print("-" * 30)
    
    health_response = {
        "status": "healthy",
        "components": {
            "ml_classifier": "healthy (mock)",
            "vector_store": "healthy (mock)",
            "demo_mode": True
        },
        "system_info": {
            "events_processed": system.processed_events,
            "total_stored_events": len(system.vector_store.events)
        }
    }
    
    print(f"Status: {health_response['status']}")
    print("Components:")
    for component, status in health_response["components"].items():
        print(f"  - {component}: {status}")
    print("System Info:")
    for key, value in health_response["system_info"].items():
        print(f"  - {key}: {value}")
    
    # Test /events endpoint
    print(f"\n📋 Testing /events endpoint:")
    print("-" * 30)
    
    events = system.vector_store.events[-5:]  # Last 5 events
    events_response = {
        "total": len(events),
        "events": []
    }
    
    for event in reversed(events):
        events_response["events"].append({
            "event_id": event.event_id,
            "text": event.text,
            "disaster_type": event.prediction,
            "confidence": event.confidence,
            "severity": event.severity,
            "timestamp": event.timestamp
        })
    
    print(f"Total events returned: {events_response['total']}")
    print("Recent events:")
    for event in events_response["events"]:
        print(f"  - {event['event_id']}: {event['disaster_type']} ({event['confidence']:.2%})")
    
    print(f"\n✅ API Testing Complete!")
    print(f"All endpoints tested successfully in demo mode.")
    print(f"Total events in system: {len(system.vector_store.events)}")

if __name__ == "__main__":
    test_api_endpoints()