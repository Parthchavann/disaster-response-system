import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from vector_search.vector_store import DisasterVectorStore


class TestDisasterVectorStore:
    
    def setup_method(self):
        with patch('vector_search.vector_store.QdrantClient'):
            self.vector_store = DisasterVectorStore()
    
    @patch('vector_search.vector_store.QdrantClient')
    def test_initialization(self, mock_client):
        # Test that vector store initializes correctly
        store = DisasterVectorStore()
        assert store.collection_name == "disaster_events"
        assert store.embedding_model is not None
    
    def test_create_embedding(self):
        with patch.object(self.vector_store.embedding_model, 'encode') as mock_encode:
            mock_encode.return_value = np.array([0.1, 0.2, 0.3])
            
            text = "Flash flood in downtown area"
            embedding = self.vector_store.create_embedding(text)
            
            assert len(embedding) == 3
            assert embedding[0] == 0.1
            mock_encode.assert_called_once_with(text)
    
    def test_add_event(self):
        with patch.object(self.vector_store, 'client') as mock_client:
            event_data = {
                "text": "Earthquake magnitude 6.5 detected",
                "disaster_type": "earthquake",
                "confidence": 0.89,
                "timestamp": "2024-01-15T10:30:00Z",
                "location": {"latitude": 37.7749, "longitude": -122.4194}
            }
            
            result = self.vector_store.add_event(event_data)
            
            assert "event_" in result  # Should return event ID
            mock_client.upsert.assert_called_once()
    
    def test_search_similar_events(self):
        with patch.object(self.vector_store, 'client') as mock_client:
            # Mock Qdrant search response
            mock_response = [
                MagicMock(
                    id="event_1",
                    score=0.95,
                    payload={
                        "text": "Major earthquake in California",
                        "disaster_type": "earthquake",
                        "confidence": 0.92
                    }
                )
            ]
            mock_client.search.return_value = mock_response
            
            results = self.vector_store.search_similar_events("earthquake", limit=5)
            
            assert len(results) == 1
            assert results[0]["disaster_type"] == "earthquake"
            assert results[0]["score"] == 0.95
            mock_client.search.assert_called_once()
    
    def test_search_by_location(self):
        with patch.object(self.vector_store, 'client') as mock_client:
            mock_response = [
                MagicMock(
                    id="event_2",
                    payload={
                        "text": "Wildfire near San Francisco",
                        "disaster_type": "fire",
                        "location": {"latitude": 37.8, "longitude": -122.4}
                    }
                )
            ]
            mock_client.scroll.return_value = (mock_response, None)
            
            lat, lon, radius = 37.7749, -122.4194, 50.0
            results = self.vector_store.search_by_location(lat, lon, radius)
            
            assert len(results) == 1
            assert results[0]["disaster_type"] == "fire"
            assert "distance_km" in results[0]
    
    def test_get_event(self):
        with patch.object(self.vector_store, 'client') as mock_client:
            mock_response = MagicMock(
                id="event_123",
                payload={
                    "text": "Hurricane approaching coast",
                    "disaster_type": "hurricane",
                    "confidence": 0.88
                }
            )
            mock_client.retrieve.return_value = [mock_response]
            
            result = self.vector_store.get_event("event_123")
            
            assert result["id"] == "event_123"
            assert result["disaster_type"] == "hurricane"
            mock_client.retrieve.assert_called_once_with(
                collection_name="disaster_events",
                ids=["event_123"]
            )
    
    def test_get_nonexistent_event(self):
        with patch.object(self.vector_store, 'client') as mock_client:
            mock_client.retrieve.return_value = []
            
            result = self.vector_store.get_event("nonexistent")
            
            assert result is None
    
    def test_haversine_distance(self):
        # Test distance calculation between NYC and Philadelphia
        lat1, lon1 = 40.7128, -74.0060  # NYC
        lat2, lon2 = 39.9526, -75.1652  # Philadelphia
        
        distance = self.vector_store.haversine_distance(lat1, lon1, lat2, lon2)
        
        # Approximate distance should be around 130-140 km
        assert 120 <= distance <= 150
    
    def test_add_location(self):
        with patch.object(self.vector_store, 'client') as mock_client:
            location_data = {
                "name": "Downtown LA",
                "latitude": 34.0522,
                "longitude": -118.2437,
                "population": 400000,
                "risk_level": "high"
            }
            
            result = self.vector_store.add_location(location_data)
            
            assert "location_" in result
            mock_client.upsert.assert_called_once()
    
    def test_index_report(self):
        with patch.object(self.vector_store, 'client') as mock_client:
            report_data = {
                "title": "Annual Disaster Response Report",
                "content": "This report analyzes disaster response effectiveness...",
                "type": "annual_report",
                "year": 2024
            }
            
            result = self.vector_store.index_report(report_data)
            
            assert "report_" in result
            mock_client.upsert.assert_called_once()
    
    def test_search_reports(self):
        with patch.object(self.vector_store, 'client') as mock_client:
            mock_response = [
                MagicMock(
                    id="report_1",
                    score=0.88,
                    payload={
                        "title": "Flood Response Analysis",
                        "type": "analysis",
                        "year": 2024
                    }
                )
            ]
            mock_client.search.return_value = mock_response
            
            results = self.vector_store.search_reports("flood analysis")
            
            assert len(results) == 1
            assert results[0]["title"] == "Flood Response Analysis"
            assert results[0]["score"] == 0.88


class TestVectorStoreIntegration:
    
    @patch('vector_search.vector_store.QdrantClient')
    def test_full_workflow(self, mock_client):
        store = DisasterVectorStore()
        
        # Add event
        event_data = {
            "text": "Tornado touchdown reported",
            "disaster_type": "tornado",
            "confidence": 0.94,
            "timestamp": "2024-01-15T16:20:00Z",
            "location": {"latitude": 35.0, "longitude": -97.0}
        }
        
        event_id = store.add_event(event_data)
        assert event_id is not None
        
        # Search for similar events
        with patch.object(store, 'client') as mock_search_client:
            mock_response = [
                MagicMock(
                    id=event_id,
                    score=1.0,
                    payload=event_data
                )
            ]
            mock_search_client.search.return_value = mock_response
            
            results = store.search_similar_events("tornado")
            assert len(results) == 1
            assert results[0]["disaster_type"] == "tornado"


if __name__ == "__main__":
    pytest.main([__file__])