"""
Kafka Producer for ingesting multimodal disaster data streams
Handles social media, weather sensors, and satellite feeds
"""

import json
import time
import random
from datetime import datetime
from typing import Dict, Any, List
from kafka import KafkaProducer
import requests
import logging
from dataclasses import dataclass
import base64
import io
from PIL import Image
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DisasterEvent:
    """Data structure for disaster events"""
    event_id: str
    timestamp: str
    event_type: str  # flood, fire, earthquake, hurricane, etc.
    location: Dict[str, float]  # lat, lon
    severity: str  # low, medium, high, critical
    confidence: float
    source: str  # social_media, weather_sensor, satellite
    data: Dict[str, Any]

class SocialMediaSimulator:
    """Simulates social media streams with disaster-related content"""
    
    def __init__(self):
        self.disaster_keywords = {
            'flood': ['flooding', 'water rising', 'river overflow', 'storm surge'],
            'fire': ['wildfire', 'smoke', 'burning', 'flames'],
            'earthquake': ['earthquake', 'shaking', 'tremor', 'quake'],
            'hurricane': ['hurricane', 'strong winds', 'storm', 'cyclone']
        }
        
        self.locations = [
            {'lat': 37.7749, 'lon': -122.4194, 'city': 'San Francisco'},
            {'lat': 34.0522, 'lon': -118.2437, 'city': 'Los Angeles'},
            {'lat': 40.7128, 'lon': -74.0060, 'city': 'New York'},
            {'lat': 25.7617, 'lon': -80.1918, 'city': 'Miami'}
        ]
    
    def generate_text_post(self) -> Dict[str, Any]:
        """Generate simulated social media text post"""
        disaster_type = random.choice(list(self.disaster_keywords.keys()))
        keyword = random.choice(self.disaster_keywords[disaster_type])
        location = random.choice(self.locations)
        
        texts = [
            f"Major {keyword} happening near {location['city']} right now!",
            f"Emergency: {keyword} reported in {location['city']} area",
            f"Breaking: {keyword} situation developing in {location['city']}",
            f"Alert: {keyword} affecting {location['city']} residents"
        ]
        
        return {
            'text': random.choice(texts),
            'location': location,
            'disaster_type': disaster_type,
            'user_id': f"user_{random.randint(1000, 9999)}",
            'platform': random.choice(['twitter', 'facebook', 'instagram'])
        }
    
    def generate_image_post(self) -> Dict[str, Any]:
        """Generate simulated image with disaster content"""
        disaster_type = random.choice(list(self.disaster_keywords.keys()))
        location = random.choice(self.locations)
        
        # Create a simple colored image to simulate disaster imagery
        colors = {
            'flood': (0, 100, 200),    # Blue tones
            'fire': (255, 100, 0),     # Orange/red tones
            'earthquake': (139, 69, 19), # Brown tones
            'hurricane': (128, 128, 128) # Gray tones
        }
        
        # Generate 256x256 image with disaster-specific color
        color = colors[disaster_type]
        img_array = np.full((256, 256, 3), color, dtype=np.uint8)
        img = Image.fromarray(img_array)
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            'image_data': img_base64,
            'location': location,
            'disaster_type': disaster_type,
            'description': f"Image showing {disaster_type} in {location['city']}",
            'user_id': f"user_{random.randint(1000, 9999)}",
            'platform': random.choice(['twitter', 'instagram', 'tiktok'])
        }

class WeatherSensorSimulator:
    """Simulates weather sensor data streams"""
    
    def generate_sensor_data(self) -> Dict[str, Any]:
        """Generate simulated weather sensor readings"""
        location = {
            'lat': round(random.uniform(25.0, 48.0), 4),
            'lon': round(random.uniform(-125.0, -65.0), 4)
        }
        
        # Simulate extreme weather conditions
        is_extreme = random.random() < 0.3  # 30% chance of extreme conditions
        
        if is_extreme:
            # Generate extreme weather data
            wind_speed = random.uniform(75, 150)  # Hurricane force
            precipitation = random.uniform(10, 50)  # Heavy rain
            temperature = random.uniform(-20, 50)  # Extreme temps
            pressure = random.uniform(950, 1050)   # Low pressure systems
        else:
            # Normal weather
            wind_speed = random.uniform(0, 25)
            precipitation = random.uniform(0, 5)
            temperature = random.uniform(0, 35)
            pressure = random.uniform(1000, 1020)
        
        return {
            'sensor_id': f"sensor_{random.randint(10000, 99999)}",
            'location': location,
            'wind_speed_mph': round(wind_speed, 2),
            'precipitation_mm': round(precipitation, 2),
            'temperature_c': round(temperature, 2),
            'pressure_hpa': round(pressure, 2),
            'humidity_percent': round(random.uniform(20, 95), 2),
            'is_extreme': is_extreme
        }

class SatelliteDataSimulator:
    """Simulates satellite imagery and environmental data"""
    
    def generate_satellite_data(self) -> Dict[str, Any]:
        """Generate simulated satellite observations"""
        location = {
            'lat': round(random.uniform(25.0, 48.0), 4),
            'lon': round(random.uniform(-125.0, -65.0), 4)
        }
        
        # Simulate different types of satellite observations
        observation_types = ['thermal', 'optical', 'radar', 'multispectral']
        obs_type = random.choice(observation_types)
        
        # Generate anomaly detection results
        has_anomaly = random.random() < 0.2  # 20% chance of anomaly
        
        return {
            'satellite_id': f"sat_{random.randint(100, 999)}",
            'observation_type': obs_type,
            'location': location,
            'resolution_m': random.choice([10, 30, 100, 250]),
            'cloud_cover_percent': round(random.uniform(0, 100), 2),
            'has_anomaly': has_anomaly,
            'anomaly_type': random.choice(['fire', 'flood', 'deforestation']) if has_anomaly else None,
            'confidence_score': round(random.uniform(0.6, 0.95), 3) if has_anomaly else None
        }

class DisasterDataProducer:
    """Main producer class for disaster response data ingestion"""
    
    def __init__(self, bootstrap_servers=['localhost:9092']):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda x: json.dumps(x).encode('utf-8'),
            key_serializer=lambda x: x.encode('utf-8') if x else None
        )
        
        self.social_media = SocialMediaSimulator()
        self.weather_sensor = WeatherSensorSimulator()
        self.satellite = SatelliteDataSimulator()
        
        # Kafka topics
        self.topics = {
            'social_media_text': 'disaster.social.text',
            'social_media_images': 'disaster.social.images',
            'weather_sensors': 'disaster.weather.sensors',
            'satellite_data': 'disaster.satellite.data'
        }
    
    def create_disaster_event(self, source: str, data: Dict[str, Any]) -> DisasterEvent:
        """Create standardized disaster event from source data"""
        event_id = f"{source}_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Extract location and disaster type from source data
        location = data.get('location', {'lat': 0.0, 'lon': 0.0})
        
        # Determine event type and severity
        if source == 'social_media':
            event_type = data.get('disaster_type', 'unknown')
            severity = random.choice(['low', 'medium', 'high'])
            confidence = random.uniform(0.6, 0.9)
        elif source == 'weather_sensor':
            if data.get('is_extreme'):
                event_type = 'severe_weather'
                severity = 'high'
                confidence = 0.95
            else:
                event_type = 'normal_weather'
                severity = 'low'
                confidence = 0.8
        elif source == 'satellite':
            if data.get('has_anomaly'):
                event_type = data.get('anomaly_type', 'unknown')
                severity = 'medium'
                confidence = data.get('confidence_score', 0.8)
            else:
                event_type = 'normal_observation'
                severity = 'low'
                confidence = 0.7
        else:
            event_type = 'unknown'
            severity = 'low'
            confidence = 0.5
        
        return DisasterEvent(
            event_id=event_id,
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            location=location,
            severity=severity,
            confidence=confidence,
            source=source,
            data=data
        )
    
    def send_to_kafka(self, topic: str, event: DisasterEvent):
        """Send disaster event to Kafka topic"""
        try:
            # Convert dataclass to dict
            event_dict = {
                'event_id': event.event_id,
                'timestamp': event.timestamp,
                'event_type': event.event_type,
                'location': event.location,
                'severity': event.severity,
                'confidence': event.confidence,
                'source': event.source,
                'data': event.data
            }
            
            future = self.producer.send(
                topic,
                key=event.event_id,
                value=event_dict
            )
            
            # Wait for the message to be sent
            record_metadata = future.get(timeout=10)
            logger.info(f"Sent event {event.event_id} to {topic} "
                       f"(partition: {record_metadata.partition}, "
                       f"offset: {record_metadata.offset})")
            
        except Exception as e:
            logger.error(f"Failed to send event to Kafka: {e}")
    
    def run_simulation(self, duration_seconds: int = 300):
        """Run data ingestion simulation"""
        logger.info(f"Starting disaster data simulation for {duration_seconds} seconds")
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration_seconds:
                # Generate different types of data randomly
                data_type = random.choice([
                    'social_text', 'social_image', 'weather', 'satellite'
                ])
                
                if data_type == 'social_text':
                    data = self.social_media.generate_text_post()
                    event = self.create_disaster_event('social_media', data)
                    self.send_to_kafka(self.topics['social_media_text'], event)
                
                elif data_type == 'social_image':
                    data = self.social_media.generate_image_post()
                    event = self.create_disaster_event('social_media', data)
                    self.send_to_kafka(self.topics['social_media_images'], event)
                
                elif data_type == 'weather':
                    data = self.weather_sensor.generate_sensor_data()
                    event = self.create_disaster_event('weather_sensor', data)
                    self.send_to_kafka(self.topics['weather_sensors'], event)
                
                elif data_type == 'satellite':
                    data = self.satellite.generate_satellite_data()
                    event = self.create_disaster_event('satellite', data)
                    self.send_to_kafka(self.topics['satellite_data'], event)
                
                # Random delay between events (0.5 to 3 seconds)
                time.sleep(random.uniform(0.5, 3.0))
        
        except KeyboardInterrupt:
            logger.info("Simulation stopped by user")
        
        finally:
            self.producer.close()
            logger.info("Kafka producer closed")

if __name__ == "__main__":
    producer = DisasterDataProducer()
    producer.run_simulation(duration_seconds=600)  # Run for 10 minutes