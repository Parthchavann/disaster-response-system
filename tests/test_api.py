import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.main import app

client = TestClient(app)


class TestHealthEndpoint:
    
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "timestamp" in data


class TestPredictEndpoint:
    
    @patch('backend.main.multimodal_model')
    def test_predict_text_only(self, mock_model):
        # Mock the model prediction
        mock_model.predict.return_value = {
            "prediction": "flood",
            "confidence": 0.85,
            "individual_confidences": {
                "text": 0.9,
                "image": 0.0,
                "weather": 0.8,
                "geo": 0.7
            }
        }
        
        payload = {
            "text": "Flash flood warning in downtown area",
            "geo": {"latitude": 40.7128, "longitude": -74.0060}
        }
        
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["prediction"] == "flood"
        assert data["confidence"] == 0.85
    
    @patch('backend.main.multimodal_model')
    def test_predict_with_weather(self, mock_model):
        mock_model.predict.return_value = {
            "prediction": "hurricane",
            "confidence": 0.92,
            "individual_confidences": {
                "text": 0.8,
                "image": 0.0,
                "weather": 0.95,
                "geo": 0.9
            }
        }
        
        payload = {
            "text": "Category 3 hurricane approaching coastline",
            "weather": {
                "wind_speed": 120.0,
                "precipitation": 50.0,
                "temperature": 28.0,
                "pressure": 940.0,
                "humidity": 85.0
            },
            "geo": {"latitude": 25.7617, "longitude": -80.1918}
        }
        
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["prediction"] == "hurricane"
        assert data["confidence"] == 0.92
    
    def test_predict_missing_data(self):
        payload = {}  # Empty payload
        
        response = client.post("/predict", json=payload)
        assert response.status_code == 400


class TestSearchEndpoint:
    
    @patch('backend.main.vector_store')
    def test_search_by_text(self, mock_vector_store):
        # Mock vector store search
        mock_vector_store.search_similar_events.return_value = [
            {
                "id": "event_1",
                "text": "Earthquake in California",
                "disaster_type": "earthquake",
                "confidence": 0.88,
                "score": 0.95
            }
        ]
        
        payload = {
            "query": "earthquake",
            "search_type": "text",
            "limit": 10
        }
        
        response = client.post("/search", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["disaster_type"] == "earthquake"
    
    @patch('backend.main.vector_store')
    def test_search_by_location(self, mock_vector_store):
        mock_vector_store.search_by_location.return_value = [
            {
                "id": "event_2",
                "location": {"latitude": 40.7128, "longitude": -74.0060},
                "disaster_type": "flood",
                "distance_km": 5.2
            }
        ]
        
        payload = {
            "search_type": "location",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "radius_km": 10.0,
            "limit": 5
        }
        
        response = client.post("/search", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["distance_km"] == 5.2


class TestStatsEndpoint:
    
    @patch('backend.main.redis_client')
    def test_get_statistics(self, mock_redis):
        # Mock Redis responses
        mock_redis.get.side_effect = lambda key: {
            "total_events": b"1542",
            "total_predictions": b"3847",
            "avg_confidence": b"0.78"
        }.get(key)
        
        response = client.get("/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_events" in data
        assert "total_predictions" in data
        assert "disaster_type_distribution" in data


class TestEventEndpoint:
    
    @patch('backend.main.vector_store')
    def test_get_event_by_id(self, mock_vector_store):
        mock_vector_store.get_event.return_value = {
            "id": "event_123",
            "text": "Wildfire spreading in forest area",
            "disaster_type": "fire",
            "confidence": 0.91,
            "timestamp": "2024-01-15T14:30:00Z",
            "location": {"latitude": 34.0522, "longitude": -118.2437}
        }
        
        response = client.get("/events/event_123")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "event_123"
        assert data["disaster_type"] == "fire"
        assert data["confidence"] == 0.91
    
    @patch('backend.main.vector_store')
    def test_get_nonexistent_event(self, mock_vector_store):
        mock_vector_store.get_event.return_value = None
        
        response = client.get("/events/nonexistent")
        assert response.status_code == 404


class TestRecentEventsEndpoint:
    
    @patch('backend.main.redis_client')
    def test_get_recent_events(self, mock_redis):
        # Mock Redis list response
        mock_events = [
            json.dumps({
                "id": "recent_1",
                "disaster_type": "tornado",
                "confidence": 0.86,
                "timestamp": "2024-01-15T15:00:00Z"
            }),
            json.dumps({
                "id": "recent_2", 
                "disaster_type": "flood",
                "confidence": 0.79,
                "timestamp": "2024-01-15T14:45:00Z"
            })
        ]
        mock_redis.lrange.return_value = [event.encode() for event in mock_events]
        
        response = client.get("/recent-events?limit=2")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 2
        assert data[0]["disaster_type"] == "tornado"


class TestWebSocketConnection:
    
    def test_websocket_connection(self):
        with client.websocket_connect("/ws/test_client") as websocket:
            # Connection should be established successfully
            assert websocket is not None
    
    @patch('backend.main.connection_manager')
    def test_websocket_alert_broadcast(self, mock_manager):
        # This would require more complex setup for WebSocket testing
        # For now, just verify the connection manager is called
        with client.websocket_connect("/ws/test_client") as websocket:
            mock_manager.connect.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])