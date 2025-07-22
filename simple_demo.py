#!/usr/bin/env python3
"""
Simple demo of the disaster response system without heavy ML dependencies.
This demonstrates the core functionality using mock models.
"""

import json
import asyncio
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import random

# Mock models to replace heavy ML dependencies
class MockDisasterClassifier:
    """Mock classifier that simulates ML predictions"""
    
    def __init__(self):
        self.disaster_labels = [
            "no_disaster", "flood", "fire", "earthquake", 
            "hurricane", "tornado", "other_disaster"
        ]
        self.disaster_keywords = {
            "flood": ["flood", "flooding", "water", "river", "rain", "overflow"],
            "fire": ["fire", "wildfire", "smoke", "burn", "flame", "forest"],
            "earthquake": ["earthquake", "quake", "tremor", "seismic", "shake"],
            "hurricane": ["hurricane", "storm", "wind", "cyclone", "typhoon"],
            "tornado": ["tornado", "twister", "funnel", "whirlwind"],
            "other_disaster": ["emergency", "disaster", "evacuation", "alert"]
        }
    
    def predict(self, text: str = None, **kwargs) -> Dict[str, Any]:
        """Mock prediction based on keywords"""
        if not text:
            text = ""
        
        text_lower = text.lower()
        predictions = {label: 0.01 for label in self.disaster_labels}
        
        # Simple keyword matching
        max_score = 0.1
        top_prediction = "no_disaster"
        
        for disaster_type, keywords in self.disaster_keywords.items():
            score = sum(0.15 for keyword in keywords if keyword in text_lower)
            if score > 0:
                score = min(score + random.uniform(0.1, 0.3), 0.95)
                predictions[disaster_type] = score
                if score > max_score:
                    max_score = score
                    top_prediction = disaster_type
        
        # Add some randomness for realism
        if max_score < 0.2:
            predictions["no_disaster"] = 0.8 + random.uniform(0, 0.15)
            top_prediction = "no_disaster"
            max_score = predictions["no_disaster"]
        
        return {
            "predictions": predictions,
            "top_prediction": top_prediction,
            "top_score": max_score,
            "confidence": max_score
        }

@dataclass
class DisasterEvent:
    """Disaster event data structure"""
    event_id: str
    text: str
    prediction: str
    confidence: float
    location: Optional[Dict[str, float]]
    timestamp: str
    severity: str
    source: str = "demo"

class MockVectorStore:
    """Mock vector store for demonstration"""
    
    def __init__(self):
        self.events = []
        self.event_counter = 0
    
    def add_event(self, event: DisasterEvent):
        """Add event to mock storage"""
        self.events.append(event)
        self.event_counter += 1
        print(f"📊 Stored event {event.event_id} in vector database")
    
    def search_similar(self, query: str, limit: int = 5):
        """Mock similarity search"""
        # Simple text matching for demo
        results = []
        query_lower = query.lower()
        
        for event in self.events:
            if any(word in event.text.lower() for word in query_lower.split()):
                score = random.uniform(0.7, 0.95)
                results.append({
                    "event": event,
                    "score": score
                })
        
        return sorted(results, key=lambda x: x["score"], reverse=True)[:limit]
    
    def get_stats(self):
        """Get database statistics"""
        disaster_counts = {}
        for event in self.events:
            disaster_counts[event.prediction] = disaster_counts.get(event.prediction, 0) + 1
        
        return {
            "total_events": len(self.events),
            "disaster_distribution": disaster_counts,
            "last_updated": datetime.now().isoformat()
        }

class DisasterResponseDemo:
    """Main demo class"""
    
    def __init__(self):
        self.classifier = MockDisasterClassifier()
        self.vector_store = MockVectorStore()
        self.processed_events = 0
    
    def determine_severity(self, confidence: float, prediction: str) -> str:
        """Determine event severity"""
        if confidence > 0.8 and prediction in ["fire", "hurricane", "earthquake"]:
            return "critical"
        elif confidence > 0.7 and prediction in ["flood", "tornado"]:
            return "high"
        elif confidence > 0.6 and prediction != "no_disaster":
            return "medium"
        else:
            return "low"
    
    def process_event(self, text: str, location: Optional[Dict[str, float]] = None) -> DisasterEvent:
        """Process a disaster event"""
        self.processed_events += 1
        
        # Generate event ID
        event_id = hashlib.md5(f"{text}_{self.processed_events}_{datetime.now()}".encode()).hexdigest()[:12]
        
        # Get prediction
        result = self.classifier.predict(text)
        
        # Determine severity
        severity = self.determine_severity(result["confidence"], result["top_prediction"])
        
        # Create event
        event = DisasterEvent(
            event_id=event_id,
            text=text,
            prediction=result["top_prediction"],
            confidence=result["confidence"],
            location=location,
            timestamp=datetime.now().isoformat(),
            severity=severity
        )
        
        # Store in vector database
        self.vector_store.add_event(event)
        
        return event
    
    def print_event_summary(self, event: DisasterEvent):
        """Print formatted event summary"""
        severity_emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "🔶", 
            "low": "ℹ️"
        }
        
        disaster_emoji = {
            "flood": "🌊",
            "fire": "🔥",
            "earthquake": "🌍",
            "hurricane": "🌀",
            "tornado": "🌪️",
            "other_disaster": "⚡",
            "no_disaster": "✅"
        }
        
        print(f"\n{severity_emoji.get(event.severity, '📊')} EVENT DETECTED")
        print(f"ID: {event.event_id}")
        print(f"Type: {disaster_emoji.get(event.prediction, '❓')} {event.prediction.upper()}")
        print(f"Confidence: {event.confidence:.2%}")
        print(f"Severity: {event.severity.upper()}")
        print(f"Text: \"{event.text}\"")
        if event.location:
            print(f"Location: {event.location['latitude']:.4f}, {event.location['longitude']:.4f}")
        print(f"Time: {event.timestamp}")
        print("-" * 50)

def run_demo():
    """Run the disaster response system demo"""
    print("🚨 DISASTER RESPONSE SYSTEM DEMO 🚨")
    print("=" * 50)
    print("Processing sample disaster reports...\n")
    
    # Initialize system
    system = DisasterResponseDemo()
    
    # Sample disaster reports
    sample_events = [
        {
            "text": "URGENT: Flash flood warning issued for downtown area. Water levels rising rapidly!",
            "location": {"latitude": 40.7128, "longitude": -74.0060}
        },
        {
            "text": "Wildfire spreading near residential areas. Evacuation ordered for zones 5-7.",
            "location": {"latitude": 34.0522, "longitude": -118.2437}
        },
        {
            "text": "Earthquake magnitude 6.2 detected. Buildings shaking, people evacuating.",
            "location": {"latitude": 37.7749, "longitude": -122.4194}
        },
        {
            "text": "Hurricane Category 3 approaching coastline. Residents advised to seek shelter.",
            "location": {"latitude": 25.7617, "longitude": -80.1918}
        },
        {
            "text": "Tornado sighted moving northeast at 45 mph. Take cover immediately!",
            "location": {"latitude": 35.2271, "longitude": -101.8313}
        },
        {
            "text": "Beautiful sunny day at the beach. Perfect weather for outdoor activities.",
            "location": {"latitude": 33.7490, "longitude": -84.3880}
        },
        {
            "text": "Emergency drill completed successfully. All systems operational.",
            "location": {"latitude": 41.8781, "longitude": -87.6298}
        }
    ]
    
    # Process each event
    events = []
    for event_data in sample_events:
        event = system.process_event(
            text=event_data["text"],
            location=event_data.get("location")
        )
        events.append(event)
        system.print_event_summary(event)
    
    # Demonstrate search functionality
    print("\n🔍 SEARCH DEMONSTRATION")
    print("=" * 50)
    print("Searching for 'flood' events...")
    
    search_results = system.vector_store.search_similar("flood")
    for i, result in enumerate(search_results, 1):
        event = result["event"]
        score = result["score"]
        print(f"{i}. [{score:.2%} match] {event.prediction}: \"{event.text[:60]}...\"")
    
    # Show system statistics
    print(f"\n📊 SYSTEM STATISTICS")
    print("=" * 50)
    stats = system.vector_store.get_stats()
    print(f"Total events processed: {stats['total_events']}")
    print("Disaster type distribution:")
    for disaster_type, count in stats['disaster_distribution'].items():
        print(f"  - {disaster_type}: {count}")
    
    # Simulate real-time API endpoint
    print(f"\n🌐 API SIMULATION")
    print("=" * 50)
    print("Simulating REST API endpoints...")
    
    # Mock API responses
    api_responses = {
        "/health": {"status": "healthy", "timestamp": datetime.now().isoformat()},
        "/stats": stats,
        "/recent-events": [asdict(event) for event in events[-3:]],
        "/search": {"query": "flood", "results": len(search_results)}
    }
    
    for endpoint, response in api_responses.items():
        print(f"GET {endpoint}")
        print(f"Response: {json.dumps(response, indent=2, default=str)[:100]}...")
        print()
    
    print("✅ Demo completed successfully!")
    print(f"The system processed {len(events)} events and demonstrated:")
    print("  - Text-based disaster classification")
    print("  - Event storage and retrieval")
    print("  - Similarity search")
    print("  - Severity assessment")
    print("  - API endpoint simulation")

if __name__ == "__main__":
    run_demo()