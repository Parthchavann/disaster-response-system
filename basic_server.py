#!/usr/bin/env python3
"""
Basic HTTP server for disaster response system demo.
Uses only Python standard library - no external dependencies.
"""

import json
import hashlib
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import random
import threading
import time

# Import our mock models
from simple_demo import MockDisasterClassifier, MockVectorStore, DisasterEvent, DisasterResponseDemo

class DisasterAPIHandler(BaseHTTPRequestHandler):
    # Class variable to share demo system across requests
    demo_system = None
    
    def __init__(self, *args, **kwargs):
        # Initialize demo system if not already done
        if DisasterAPIHandler.demo_system is None:
            DisasterAPIHandler.demo_system = DisasterResponseDemo()
            # Load some sample data
            self._load_sample_data()
        super().__init__(*args, **kwargs)
    
    def _load_sample_data(self):
        """Load sample data for demonstration"""
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
                "text": "Beautiful sunny day at the beach. Perfect weather for outdoor activities.",
                "location": {"latitude": 33.7490, "longitude": -84.3880}
            }
        ]
        
        for event_data in sample_events:
            self.demo_system.process_event(
                text=event_data["text"],
                location=event_data.get("location")
            )
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json')
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        try:
            if path == '/':
                self._handle_root()
            elif path == '/health':
                self._handle_health()
            elif path == '/stats':
                self._handle_stats()
            elif path == '/events':
                limit = int(query_params.get('limit', [20])[0])
                self._handle_events(limit)
            elif path.startswith('/events/'):
                event_id = path.split('/')[-1]
                self._handle_get_event(event_id)
            else:
                self._send_error(404, "Not Found")
        except Exception as e:
            self._send_error(500, f"Internal Server Error: {str(e)}")
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        try:
            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            if path == '/predict':
                data = json.loads(post_data) if post_data else {}
                self._handle_predict(data)
            elif path == '/search':
                data = json.loads(post_data) if post_data else {}
                self._handle_search(data)
            else:
                self._send_error(404, "Not Found")
        except Exception as e:
            self._send_error(500, f"Internal Server Error: {str(e)}")
    
    def _handle_root(self):
        """Handle root endpoint"""
        response = {
            "message": "Disaster Response API - Basic Demo",
            "version": "1.0.0-basic",
            "status": "operational",
            "note": "This is a basic demo server using Python standard library only",
            "endpoints": {
                "predict": "/predict",
                "search": "/search", 
                "stats": "/stats",
                "health": "/health",
                "events": "/events"
            }
        }
        self._send_json_response(200, response)
    
    def _handle_health(self):
        """Handle health check"""
        response = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "ml_classifier": "healthy (mock)",
                "vector_store": "healthy (mock)",
                "demo_mode": True
            },
            "system_info": {
                "events_processed": self.demo_system.processed_events,
                "total_stored_events": len(self.demo_system.vector_store.events)
            }
        }
        self._send_json_response(200, response)
    
    def _handle_stats(self):
        """Handle stats endpoint"""
        stats = self.demo_system.vector_store.get_stats()
        response = {
            "system_status": "operational (basic demo)",
            "timestamp": datetime.now().isoformat(),
            "total_events": stats["total_events"],
            "events_processed": self.demo_system.processed_events,
            "disaster_type_distribution": stats["disaster_distribution"],
            "last_updated": stats["last_updated"],
            "demo_mode": True
        }
        self._send_json_response(200, response)
    
    def _handle_events(self, limit):
        """Handle events endpoint"""
        events = self.demo_system.vector_store.events[-limit:]
        
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
        
        response = {
            "total": len(formatted_events),
            "events": formatted_events
        }
        self._send_json_response(200, response)
    
    def _handle_get_event(self, event_id):
        """Handle get specific event"""
        for event in self.demo_system.vector_store.events:
            if event.event_id == event_id:
                response = {
                    "event_id": event.event_id,
                    "text": event.text,
                    "disaster_type": event.prediction,
                    "confidence": event.confidence,
                    "severity": event.severity,
                    "location": event.location,
                    "timestamp": event.timestamp,
                    "source": event.source
                }
                self._send_json_response(200, response)
                return
        
        self._send_error(404, "Event not found")
    
    def _handle_predict(self, data):
        """Handle prediction endpoint"""
        text = data.get('text', '')
        location = data.get('location')
        
        if not text:
            self._send_error(400, "Text is required for prediction")
            return
        
        start_time = datetime.now()
        
        # Process the event
        event = self.demo_system.process_event(text=text, location=location)
        
        # Get detailed predictions
        result = self.demo_system.classifier.predict(text)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        response = {
            "event_id": event.event_id,
            "predictions": result["predictions"],
            "top_prediction": event.prediction,
            "confidence_score": event.confidence,
            "severity": event.severity,
            "location": location,
            "timestamp": event.timestamp,
            "processing_time_ms": processing_time
        }
        
        self._send_json_response(200, response)
    
    def _handle_search(self, data):
        """Handle search endpoint"""
        query = data.get('query', '')
        limit = data.get('limit', 10)
        
        if not query:
            self._send_error(400, "Query is required for search")
            return
        
        results = self.demo_system.vector_store.search_similar(query=query, limit=limit)
        
        formatted_results = []
        for result in results:
            event = result["event"]
            formatted_results.append({
                "event_id": event.event_id,
                "text": event.text,
                "disaster_type": event.prediction,
                "confidence": event.confidence,
                "severity": event.severity,
                "location": event.location,
                "timestamp": event.timestamp,
                "score": result["score"]
            })
        
        response = {
            "query": query,
            "total_results": len(formatted_results),
            "results": formatted_results
        }
        
        self._send_json_response(200, response)
    
    def _send_json_response(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode('utf-8'))
    
    def _send_error(self, status_code, message):
        """Send error response"""
        self.send_response(status_code)
        self.send_cors_headers()
        self.end_headers()
        error_response = {"error": message, "status_code": status_code}
        self.wfile.write(json.dumps(error_response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to customize logging"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {format % args}")

def run_server(host='localhost', port=8000):
    """Run the HTTP server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, DisasterAPIHandler)
    
    print("🚨 Starting Disaster Response API Server (Basic Mode)")
    print("=" * 60)
    print(f"🌐 Server running at: http://{host}:{port}")
    print(f"📖 Root endpoint: http://{host}:{port}/")
    print(f"💚 Health check: http://{host}:{port}/health")
    print(f"📊 Statistics: http://{host}:{port}/stats")
    print(f"🔍 Recent events: http://{host}:{port}/events")
    print("=" * 60)
    print("🔥 Ready to handle disaster response requests!")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        httpd.server_close()

if __name__ == "__main__":
    run_server(host='0.0.0.0', port=8000)