"""
Vector Search and Retrieval System for Disaster Response
Uses Qdrant for efficient similarity search and location-based queries
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import json
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, Range, MatchValue,
    SearchRequest, SearchParams, HasIdCondition
)
import uuid
from sentence_transformers import SentenceTransformer
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DisasterVectorStore:
    """Vector database for disaster event storage and retrieval"""
    
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dim = 384  # Dimension of all-MiniLM-L6-v2
        
        # Collection names
        self.collections = {
            'disaster_events': 'disaster_events',
            'locations': 'disaster_locations',
            'reports': 'disaster_reports'
        }
        
        self.setup_collections()
    
    def setup_collections(self):
        """Create vector collections if they don't exist"""
        
        # Disaster events collection
        try:
            self.client.create_collection(
                collection_name=self.collections['disaster_events'],
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
            logger.info("Created disaster_events collection")
        except Exception as e:
            logger.info(f"Collection disaster_events already exists or error: {e}")
        
        # Locations collection (for geo-based search)
        try:
            self.client.create_collection(
                collection_name=self.collections['locations'],
                vectors_config=VectorParams(
                    size=2,  # Just lat/lon for geo search
                    distance=Distance.EUCLID
                )
            )
            logger.info("Created disaster_locations collection")
        except Exception as e:
            logger.info(f"Collection disaster_locations already exists or error: {e}")
        
        # Reports collection (for RAG)
        try:
            self.client.create_collection(
                collection_name=self.collections['reports'],
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
            logger.info("Created disaster_reports collection")
        except Exception as e:
            logger.info(f"Collection disaster_reports already exists or error: {e}")
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embeddings for text"""
        return self.embedding_model.encode(text, convert_to_numpy=True)
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts"""
        return self.embedding_model.encode(texts, convert_to_numpy=True)
    
    def index_disaster_event(self, event: Dict[str, Any]) -> str:
        """Index a disaster event in the vector store"""
        
        # Generate unique ID
        event_id = event.get('event_id', str(uuid.uuid4()))
        
        # Create text representation for embedding
        text_parts = []
        if 'text' in event:
            text_parts.append(event['text'])
        if 'description' in event:
            text_parts.append(event['description'])
        if 'event_type' in event:
            text_parts.append(f"Disaster type: {event['event_type']}")
        if 'severity' in event:
            text_parts.append(f"Severity: {event['severity']}")
        
        event_text = " ".join(text_parts)
        
        # Generate embedding
        embedding = self.embed_text(event_text)
        
        # Prepare payload
        payload = {
            'event_id': event_id,
            'timestamp': event.get('timestamp', datetime.now().isoformat()),
            'event_type': event.get('event_type', 'unknown'),
            'severity': event.get('severity', 'unknown'),
            'confidence': event.get('confidence', 0.0),
            'source': event.get('source', 'unknown'),
            'location': event.get('location', {}),
            'text': event_text,
            'original_data': json.dumps(event)
        }
        
        # Create point
        point = PointStruct(
            id=event_id,
            vector=embedding.tolist(),
            payload=payload
        )
        
        # Insert into collection
        self.client.upsert(
            collection_name=self.collections['disaster_events'],
            points=[point]
        )
        
        # Also index location if available
        if 'location' in event and 'lat' in event['location'] and 'lon' in event['location']:
            self.index_location(event_id, event['location'])
        
        logger.info(f"Indexed disaster event: {event_id}")
        return event_id
    
    def index_location(self, event_id: str, location: Dict[str, float]):
        """Index location for geo-based search"""
        
        # Create location vector (just lat/lon)
        location_vector = [location['lat'], location['lon']]
        
        # Location ID (hash of coordinates)
        location_id = hashlib.md5(
            f"{location['lat']}_{location['lon']}".encode()
        ).hexdigest()
        
        # Payload
        payload = {
            'event_id': event_id,
            'lat': location['lat'],
            'lon': location['lon'],
            'city': location.get('city', 'Unknown'),
            'indexed_at': datetime.now().isoformat()
        }
        
        # Create point
        point = PointStruct(
            id=location_id,
            vector=location_vector,
            payload=payload
        )
        
        # Insert into location collection
        self.client.upsert(
            collection_name=self.collections['locations'],
            points=[point]
        )
    
    def search_similar_events(self, query_text: str, 
                            event_type: Optional[str] = None,
                            severity: Optional[str] = None,
                            limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar disaster events"""
        
        # Generate query embedding
        query_embedding = self.embed_text(query_text)
        
        # Build filter conditions
        filter_conditions = []
        if event_type:
            filter_conditions.append(
                FieldCondition(
                    key="event_type",
                    match=MatchValue(value=event_type)
                )
            )
        if severity:
            filter_conditions.append(
                FieldCondition(
                    key="severity",
                    match=MatchValue(value=severity)
                )
            )
        
        # Create filter
        search_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        # Perform search
        search_result = self.client.search(
            collection_name=self.collections['disaster_events'],
            query_vector=query_embedding.tolist(),
            query_filter=search_filter,
            limit=limit
        )
        
        # Process results
        results = []
        for hit in search_result:
            result = {
                'id': hit.id,
                'score': hit.score,
                'event': hit.payload
            }
            results.append(result)
        
        return results
    
    def search_by_location(self, lat: float, lon: float, 
                          radius_km: float = 50.0,
                          limit: int = 20) -> List[Dict[str, Any]]:
        """Search for events near a location"""
        
        # Convert radius to approximate degrees
        # 1 degree latitude ≈ 111 km
        radius_degrees = radius_km / 111.0
        
        # Search in location collection
        location_results = self.client.search(
            collection_name=self.collections['locations'],
            query_vector=[lat, lon],
            limit=limit * 2  # Get more to filter by radius
        )
        
        # Filter by actual distance and get event details
        results = []
        event_ids = set()
        
        for hit in location_results:
            # Calculate actual distance
            hit_lat = hit.payload['lat']
            hit_lon = hit.payload['lon']
            distance = self._haversine_distance(lat, lon, hit_lat, hit_lon)
            
            if distance <= radius_km:
                event_id = hit.payload['event_id']
                if event_id not in event_ids:
                    event_ids.add(event_id)
                    
                    # Get full event details
                    event = self.get_event_by_id(event_id)
                    if event:
                        results.append({
                            'distance_km': distance,
                            'location': {
                                'lat': hit_lat,
                                'lon': hit_lon,
                                'city': hit.payload.get('city', 'Unknown')
                            },
                            'event': event
                        })
        
        # Sort by distance
        results.sort(key=lambda x: x['distance_km'])
        return results[:limit]
    
    def search_by_time_range(self, start_time: datetime, end_time: datetime,
                           event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for events within a time range"""
        
        # Build filter
        filter_conditions = [
            FieldCondition(
                key="timestamp",
                range=Range(
                    gte=start_time.isoformat(),
                    lte=end_time.isoformat()
                )
            )
        ]
        
        if event_type:
            filter_conditions.append(
                FieldCondition(
                    key="event_type",
                    match=MatchValue(value=event_type)
                )
            )
        
        # Search with filter
        search_result = self.client.scroll(
            collection_name=self.collections['disaster_events'],
            scroll_filter=Filter(must=filter_conditions),
            limit=1000  # Get all matching events
        )
        
        # Process results
        results = []
        for point in search_result[0]:
            results.append({
                'id': point.id,
                'event': point.payload
            })
        
        # Sort by timestamp
        results.sort(key=lambda x: x['event']['timestamp'])
        return results
    
    def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve specific event by ID"""
        
        try:
            result = self.client.retrieve(
                collection_name=self.collections['disaster_events'],
                ids=[event_id]
            )
            
            if result:
                return result[0].payload
            return None
        except Exception as e:
            logger.error(f"Error retrieving event {event_id}: {e}")
            return None
    
    def index_report(self, report: Dict[str, Any]) -> str:
        """Index a disaster report for RAG"""
        
        report_id = report.get('report_id', str(uuid.uuid4()))
        
        # Create text for embedding
        report_text = f"{report.get('title', '')} {report.get('content', '')}"
        
        # Generate embedding
        embedding = self.embed_text(report_text)
        
        # Prepare payload
        payload = {
            'report_id': report_id,
            'title': report.get('title', ''),
            'content': report.get('content', ''),
            'event_ids': report.get('event_ids', []),
            'created_at': report.get('created_at', datetime.now().isoformat()),
            'report_type': report.get('report_type', 'general'),
            'metadata': report.get('metadata', {})
        }
        
        # Create point
        point = PointStruct(
            id=report_id,
            vector=embedding.tolist(),
            payload=payload
        )
        
        # Insert into reports collection
        self.client.upsert(
            collection_name=self.collections['reports'],
            points=[point]
        )
        
        logger.info(f"Indexed report: {report_id}")
        return report_id
    
    def search_reports(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search disaster reports for RAG"""
        
        # Generate query embedding
        query_embedding = self.embed_text(query)
        
        # Search reports
        search_result = self.client.search(
            collection_name=self.collections['reports'],
            query_vector=query_embedding.tolist(),
            limit=limit
        )
        
        # Process results
        results = []
        for hit in search_result:
            results.append({
                'score': hit.score,
                'report': hit.payload
            })
        
        return results
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored events"""
        
        # Get collection info
        events_info = self.client.get_collection(self.collections['disaster_events'])
        locations_info = self.client.get_collection(self.collections['locations'])
        reports_info = self.client.get_collection(self.collections['reports'])
        
        stats = {
            'total_events': events_info.points_count,
            'total_locations': locations_info.points_count,
            'total_reports': reports_info.points_count,
            'collections': {
                'events': {
                    'count': events_info.points_count,
                    'vector_size': events_info.config.params.vectors.size
                },
                'locations': {
                    'count': locations_info.points_count,
                    'vector_size': locations_info.config.params.vectors.size
                },
                'reports': {
                    'count': reports_info.points_count,
                    'vector_size': reports_info.config.params.vectors.size
                }
            }
        }
        
        return stats
    
    def _haversine_distance(self, lat1: float, lon1: float, 
                           lat2: float, lon2: float) -> float:
        """Calculate distance between two points on Earth in km"""
        R = 6371  # Earth's radius in km
        
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        
        a = (np.sin(dlat/2)**2 + 
             np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * 
             np.sin(dlon/2)**2)
        
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c
    
    def create_geospatial_index(self):
        """Create additional geospatial indexing (future enhancement)"""
        # This would integrate with PostGIS or similar for advanced geo queries
        pass

def main():
    """Test the vector store"""
    
    # Initialize vector store
    vector_store = DisasterVectorStore()
    
    # Test data
    test_events = [
        {
            'event_id': 'test_001',
            'timestamp': datetime.now().isoformat(),
            'event_type': 'flood',
            'severity': 'high',
            'confidence': 0.85,
            'text': 'Major flooding reported in downtown area, several streets underwater',
            'location': {'lat': 25.7617, 'lon': -80.1918, 'city': 'Miami'},
            'source': 'social_media'
        },
        {
            'event_id': 'test_002',
            'timestamp': datetime.now().isoformat(),
            'event_type': 'fire',
            'severity': 'critical',
            'confidence': 0.92,
            'text': 'Wildfire spreading rapidly through forest, evacuation ordered',
            'location': {'lat': 34.0522, 'lon': -118.2437, 'city': 'Los Angeles'},
            'source': 'satellite'
        }
    ]
    
    # Index events
    for event in test_events:
        event_id = vector_store.index_disaster_event(event)
        print(f"Indexed event: {event_id}")
    
    # Test similarity search
    print("\n--- Similarity Search ---")
    results = vector_store.search_similar_events("flooding water damage", limit=5)
    for result in results:
        print(f"Score: {result['score']:.3f}, Type: {result['event']['event_type']}, "
              f"Text: {result['event']['text'][:50]}...")
    
    # Test location search
    print("\n--- Location Search (Miami area) ---")
    location_results = vector_store.search_by_location(25.7617, -80.1918, radius_km=100)
    for result in location_results:
        print(f"Distance: {result['distance_km']:.1f}km, "
              f"Type: {result['event']['event_type']}, "
              f"City: {result['location']['city']}")
    
    # Test report indexing
    test_report = {
        'report_id': 'report_001',
        'title': 'Hurricane Season 2024 Summary',
        'content': 'This report summarizes the major hurricane events and their impacts...',
        'event_ids': ['test_001', 'test_002'],
        'report_type': 'summary'
    }
    
    report_id = vector_store.index_report(test_report)
    print(f"\nIndexed report: {report_id}")
    
    # Get statistics
    stats = vector_store.get_event_statistics()
    print(f"\nVector Store Statistics:")
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    main()