"""
Feature Engineering Pipeline for Disaster Response System
Uses Feast feature store for managing and serving features
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from feast import FeatureStore, Entity, Feature, FeatureView, FileSource, ValueType
from feast.data_source import DataSource
from feast.on_demand_feature_view import on_demand_feature_view
from feast.types import Float32, Float64, Int64, String, UnixTimestamp
import json
import hashlib
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from scipy import signal
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DisasterFeatureEngineering:
    """Feature engineering pipeline for disaster response data"""
    
    def __init__(self, feature_repo_path: str = "./feature_repo"):
        self.feature_repo_path = feature_repo_path
        self.scaler = StandardScaler()
        
        # Feature extractors
        self.text_feature_extractor = TextFeatureExtractor()
        self.image_feature_extractor = ImageFeatureExtractor()
        self.weather_feature_extractor = WeatherFeatureExtractor()
        self.geo_feature_extractor = GeospatialFeatureExtractor()
        
    def extract_text_features(self, text_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from text data"""
        return self.text_feature_extractor.extract(text_data)
    
    def extract_image_features(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from image data"""
        return self.image_feature_extractor.extract(image_data)
    
    def extract_weather_features(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from weather sensor data"""
        return self.weather_feature_extractor.extract(weather_data)
    
    def extract_geo_features(self, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract geospatial features"""
        return self.geo_feature_extractor.extract(location_data)
    
    def create_feature_vector(self, event_data: Dict[str, Any]) -> np.ndarray:
        """Create comprehensive feature vector from multimodal data"""
        features = []
        
        # Extract features based on available data
        if 'text' in event_data:
            text_features = self.extract_text_features(event_data)
            features.extend([
                text_features['text_length'],
                text_features['urgency_score'],
                text_features['disaster_keyword_count'],
                text_features['sentiment_score'],
                text_features['caps_ratio']
            ])
        
        if 'weather' in event_data:
            weather_features = self.extract_weather_features(event_data['weather'])
            features.extend([
                weather_features['wind_speed_normalized'],
                weather_features['precipitation_normalized'],
                weather_features['pressure_anomaly'],
                weather_features['extreme_weather_score'],
                weather_features['weather_volatility']
            ])
        
        if 'location' in event_data:
            geo_features = self.extract_geo_features(event_data['location'])
            features.extend([
                geo_features['lat_normalized'],
                geo_features['lon_normalized'],
                geo_features['coastal_proximity'],
                geo_features['elevation_risk'],
                geo_features['population_density_score']
            ])
        
        return np.array(features)

class TextFeatureExtractor:
    """Extract features from text data"""
    
    def __init__(self):
        self.disaster_keywords = {
            'urgent': ['urgent', 'emergency', 'help', '911', 'sos', 'critical'],
            'flood': ['flood', 'water', 'rising', 'overflow', 'submerged', 'drowning'],
            'fire': ['fire', 'smoke', 'burning', 'flames', 'wildfire', 'blaze'],
            'earthquake': ['earthquake', 'quake', 'tremor', 'shaking', 'collapse', 'rubble'],
            'hurricane': ['hurricane', 'storm', 'winds', 'cyclone', 'typhoon', 'surge'],
            'general': ['disaster', 'evacuate', 'danger', 'warning', 'alert', 'rescue']
        }
    
    def extract(self, text_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text features"""
        text = text_data.get('text', '').lower()
        
        features = {
            'text_length': len(text),
            'word_count': len(text.split()),
            'urgency_score': self._calculate_urgency_score(text),
            'disaster_keyword_count': self._count_disaster_keywords(text),
            'caps_ratio': self._calculate_caps_ratio(text_data.get('text', '')),
            'exclamation_count': text.count('!'),
            'question_count': text.count('?'),
            'hashtag_count': len(re.findall(r'#\w+', text)),
            'mention_count': len(re.findall(r'@\w+', text)),
            'url_count': len(re.findall(r'http[s]?://\S+', text)),
            'sentiment_score': self._estimate_sentiment(text),
            'text_hash': hashlib.md5(text.encode()).hexdigest()
        }
        
        # Add keyword category scores
        for category, keywords in self.disaster_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            features[f'{category}_keyword_score'] = score
        
        return features
    
    def _calculate_urgency_score(self, text: str) -> float:
        """Calculate urgency score based on keywords and patterns"""
        urgency_score = 0.0
        
        # Check for urgent keywords
        urgent_keywords = self.disaster_keywords['urgent']
        for keyword in urgent_keywords:
            if keyword in text:
                urgency_score += 0.2
        
        # Check for capital letters (shouting)
        if len(text) > 0:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            urgency_score += min(caps_ratio * 0.5, 0.3)
        
        # Check for multiple exclamation marks
        urgency_score += min(text.count('!') * 0.1, 0.3)
        
        return min(urgency_score, 1.0)
    
    def _count_disaster_keywords(self, text: str) -> int:
        """Count total disaster-related keywords"""
        count = 0
        for category, keywords in self.disaster_keywords.items():
            for keyword in keywords:
                count += text.count(keyword)
        return count
    
    def _calculate_caps_ratio(self, text: str) -> float:
        """Calculate ratio of capital letters"""
        if len(text) == 0:
            return 0.0
        return sum(1 for c in text if c.isupper()) / len(text)
    
    def _estimate_sentiment(self, text: str) -> float:
        """Simple sentiment estimation (-1 to 1)"""
        negative_words = ['bad', 'terrible', 'awful', 'disaster', 'danger', 'help']
        positive_words = ['safe', 'okay', 'good', 'clear', 'calm']
        
        neg_score = sum(1 for word in negative_words if word in text)
        pos_score = sum(1 for word in positive_words if word in text)
        
        if neg_score + pos_score == 0:
            return 0.0
        
        return (pos_score - neg_score) / (pos_score + neg_score)

class ImageFeatureExtractor:
    """Extract features from image data"""
    
    def extract(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract image features"""
        features = {
            'has_image': 1 if image_data.get('image_data') else 0,
            'image_size': len(image_data.get('image_data', '')) if image_data.get('image_data') else 0,
            'platform': image_data.get('platform', 'unknown'),
            'description_length': len(image_data.get('description', '')),
            'disaster_type_mentioned': image_data.get('disaster_type', 'unknown')
        }
        
        # Add platform-specific features
        platform = image_data.get('platform', '').lower()
        features['is_twitter'] = 1 if platform == 'twitter' else 0
        features['is_instagram'] = 1 if platform == 'instagram' else 0
        features['is_facebook'] = 1 if platform == 'facebook' else 0
        
        return features

class WeatherFeatureExtractor:
    """Extract features from weather sensor data"""
    
    def __init__(self):
        # Normal ranges for weather parameters
        self.normal_ranges = {
            'wind_speed_mph': (0, 25),
            'precipitation_mm': (0, 10),
            'temperature_c': (10, 25),
            'pressure_hpa': (1000, 1020),
            'humidity_percent': (30, 70)
        }
    
    def extract(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract weather features"""
        features = {}
        
        # Basic weather measurements
        wind_speed = weather_data.get('wind_speed_mph', 0)
        precipitation = weather_data.get('precipitation_mm', 0)
        temperature = weather_data.get('temperature_c', 20)
        pressure = weather_data.get('pressure_hpa', 1013)
        humidity = weather_data.get('humidity_percent', 50)
        
        # Normalized features
        features['wind_speed_normalized'] = self._normalize_value(
            wind_speed, 0, 150
        )
        features['precipitation_normalized'] = self._normalize_value(
            precipitation, 0, 100
        )
        features['temperature_normalized'] = self._normalize_value(
            temperature, -50, 50
        )
        features['pressure_normalized'] = self._normalize_value(
            pressure, 950, 1050
        )
        features['humidity_normalized'] = self._normalize_value(
            humidity, 0, 100
        )
        
        # Anomaly scores
        features['wind_anomaly'] = self._calculate_anomaly_score(
            wind_speed, self.normal_ranges['wind_speed_mph']
        )
        features['precipitation_anomaly'] = self._calculate_anomaly_score(
            precipitation, self.normal_ranges['precipitation_mm']
        )
        features['pressure_anomaly'] = self._calculate_anomaly_score(
            pressure, self.normal_ranges['pressure_hpa']
        )
        
        # Extreme weather score
        features['extreme_weather_score'] = self._calculate_extreme_weather_score(
            wind_speed, precipitation, pressure, temperature
        )
        
        # Weather volatility (would need historical data in real scenario)
        features['weather_volatility'] = np.random.uniform(0, 1)  # Placeholder
        
        # Specific weather conditions
        features['is_hurricane_conditions'] = 1 if wind_speed > 74 else 0
        features['is_heavy_rain'] = 1 if precipitation > 25 else 0
        features['is_low_pressure'] = 1 if pressure < 990 else 0
        features['is_extreme_temp'] = 1 if temperature < -10 or temperature > 40 else 0
        
        return features
    
    def _normalize_value(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize value to 0-1 range"""
        return np.clip((value - min_val) / (max_val - min_val), 0, 1)
    
    def _calculate_anomaly_score(self, value: float, normal_range: tuple) -> float:
        """Calculate how anomalous a value is"""
        min_normal, max_normal = normal_range
        
        if min_normal <= value <= max_normal:
            return 0.0
        
        if value < min_normal:
            deviation = (min_normal - value) / min_normal
        else:
            deviation = (value - max_normal) / max_normal
        
        return min(deviation, 1.0)
    
    def _calculate_extreme_weather_score(self, wind: float, rain: float, 
                                       pressure: float, temp: float) -> float:
        """Calculate overall extreme weather score"""
        score = 0.0
        
        # Wind contribution
        if wind > 50:
            score += 0.3 * min(wind / 100, 1.0)
        
        # Rain contribution
        if rain > 20:
            score += 0.3 * min(rain / 50, 1.0)
        
        # Pressure contribution (low pressure is bad)
        if pressure < 990:
            score += 0.2 * min((1000 - pressure) / 50, 1.0)
        
        # Temperature extremes
        if temp < -10 or temp > 40:
            score += 0.2
        
        return min(score, 1.0)

class GeospatialFeatureExtractor:
    """Extract geospatial features"""
    
    def __init__(self):
        # Major disaster-prone areas (simplified)
        self.coastal_cities = [
            {'lat': 25.7617, 'lon': -80.1918, 'name': 'Miami'},
            {'lat': 29.7604, 'lon': -95.3698, 'name': 'Houston'},
            {'lat': 32.7767, 'lon': -96.7970, 'name': 'Dallas'}
        ]
        
        self.earthquake_zones = [
            {'lat': 34.0522, 'lon': -118.2437, 'name': 'Los Angeles'},
            {'lat': 37.7749, 'lon': -122.4194, 'name': 'San Francisco'},
            {'lat': 47.6062, 'lon': -122.3321, 'name': 'Seattle'}
        ]
    
    def extract(self, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract geospatial features"""
        lat = location_data.get('lat', 0.0)
        lon = location_data.get('lon', 0.0)
        
        features = {
            'lat': lat,
            'lon': lon,
            'lat_normalized': (lat + 90) / 180,  # Normalize to 0-1
            'lon_normalized': (lon + 180) / 360,  # Normalize to 0-1
            'abs_latitude': abs(lat),
            'hemisphere': 1 if lat >= 0 else 0,
            'coastal_proximity': self._calculate_coastal_proximity(lat, lon),
            'earthquake_zone_proximity': self._calculate_earthquake_proximity(lat, lon),
            'elevation_risk': self._estimate_elevation_risk(lat, lon),
            'population_density_score': self._estimate_population_density(lat, lon),
            'disaster_prone_score': self._calculate_disaster_prone_score(lat, lon)
        }
        
        # Time-based features
        features['season_risk'] = self._calculate_seasonal_risk(lat)
        features['daylight_hours'] = self._estimate_daylight_hours(lat)
        
        return features
    
    def _calculate_coastal_proximity(self, lat: float, lon: float) -> float:
        """Calculate proximity to coastal areas"""
        min_distance = float('inf')
        
        for city in self.coastal_cities:
            distance = self._haversine_distance(lat, lon, city['lat'], city['lon'])
            min_distance = min(min_distance, distance)
        
        # Convert to 0-1 score (closer = higher score)
        return max(0, 1 - min_distance / 1000)  # Within 1000km
    
    def _calculate_earthquake_proximity(self, lat: float, lon: float) -> float:
        """Calculate proximity to earthquake zones"""
        min_distance = float('inf')
        
        for city in self.earthquake_zones:
            distance = self._haversine_distance(lat, lon, city['lat'], city['lon'])
            min_distance = min(min_distance, distance)
        
        return max(0, 1 - min_distance / 1000)
    
    def _haversine_distance(self, lat1: float, lon1: float, 
                           lat2: float, lon2: float) -> float:
        """Calculate distance between two points on Earth"""
        R = 6371  # Earth's radius in km
        
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        
        a = (np.sin(dlat/2)**2 + 
             np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * 
             np.sin(dlon/2)**2)
        
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c
    
    def _estimate_elevation_risk(self, lat: float, lon: float) -> float:
        """Estimate elevation-based risk (placeholder)"""
        # In real implementation, would use elevation data
        # Low elevation = higher flood risk
        return np.random.uniform(0, 1)
    
    def _estimate_population_density(self, lat: float, lon: float) -> float:
        """Estimate population density (placeholder)"""
        # In real implementation, would use population data
        # Higher density = more people at risk
        return np.random.uniform(0, 1)
    
    def _calculate_disaster_prone_score(self, lat: float, lon: float) -> float:
        """Calculate overall disaster prone score"""
        coastal = self._calculate_coastal_proximity(lat, lon)
        earthquake = self._calculate_earthquake_proximity(lat, lon)
        
        # Weighted combination
        return 0.5 * coastal + 0.5 * earthquake
    
    def _calculate_seasonal_risk(self, lat: float) -> float:
        """Calculate seasonal disaster risk based on latitude"""
        # Hurricane season in tropical regions
        if 10 <= abs(lat) <= 30:
            return 0.8
        # Winter storm risk in higher latitudes
        elif abs(lat) > 50:
            return 0.6
        else:
            return 0.3
    
    def _estimate_daylight_hours(self, lat: float) -> float:
        """Estimate daylight hours based on latitude"""
        # Simplified estimation
        return 12 + 6 * np.sin(np.radians(lat))

class FeastFeatureStore:
    """Feast feature store integration for disaster response features"""
    
    def __init__(self, repo_path: str = "./feature_repo"):
        self.repo_path = repo_path
        self.fs = None
    
    def setup_feature_definitions(self):
        """Define Feast features for disaster response"""
        
        # Entity definitions
        disaster_event = Entity(
            name="disaster_event",
            value_type=ValueType.STRING,
            description="Unique identifier for disaster event"
        )
        
        location = Entity(
            name="location",
            value_type=ValueType.STRING,
            description="Location identifier (lat_lon hash)"
        )
        
        # Feature definitions for text features
        text_features = [
            Feature(name="text_length", dtype=ValueType.INT64),
            Feature(name="urgency_score", dtype=ValueType.FLOAT),
            Feature(name="disaster_keyword_count", dtype=ValueType.INT64),
            Feature(name="sentiment_score", dtype=ValueType.FLOAT),
            Feature(name="caps_ratio", dtype=ValueType.FLOAT),
        ]
        
        # Feature definitions for weather features
        weather_features = [
            Feature(name="wind_speed_normalized", dtype=ValueType.FLOAT),
            Feature(name="precipitation_normalized", dtype=ValueType.FLOAT),
            Feature(name="pressure_anomaly", dtype=ValueType.FLOAT),
            Feature(name="extreme_weather_score", dtype=ValueType.FLOAT),
            Feature(name="weather_volatility", dtype=ValueType.FLOAT),
        ]
        
        # Feature definitions for geospatial features
        geo_features = [
            Feature(name="coastal_proximity", dtype=ValueType.FLOAT),
            Feature(name="earthquake_zone_proximity", dtype=ValueType.FLOAT),
            Feature(name="elevation_risk", dtype=ValueType.FLOAT),
            Feature(name="population_density_score", dtype=ValueType.FLOAT),
            Feature(name="disaster_prone_score", dtype=ValueType.FLOAT),
        ]
        
        return {
            'entities': [disaster_event, location],
            'text_features': text_features,
            'weather_features': weather_features,
            'geo_features': geo_features
        }
    
    def create_feature_views(self):
        """Create Feast feature views"""
        # This would be implemented with actual Feast feature view definitions
        # connecting to the data sources (Parquet files, BigQuery, etc.)
        pass

def main():
    """Test the feature engineering pipeline"""
    
    # Initialize feature engineering
    feature_eng = DisasterFeatureEngineering()
    
    # Test data
    test_event = {
        'text': "URGENT! Massive flooding in downtown area, water rising fast! Need help!!!",
        'weather': {
            'wind_speed_mph': 85,
            'precipitation_mm': 45,
            'temperature_c': 22,
            'pressure_hpa': 980,
            'humidity_percent': 95
        },
        'location': {
            'lat': 25.7617,
            'lon': -80.1918
        }
    }
    
    # Extract features
    text_features = feature_eng.extract_text_features(test_event)
    weather_features = feature_eng.extract_weather_features(test_event['weather'])
    geo_features = feature_eng.extract_geo_features(test_event['location'])
    
    print("Text Features:")
    for key, value in text_features.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
    
    print("\nWeather Features:")
    for key, value in weather_features.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
    
    print("\nGeospatial Features:")
    for key, value in geo_features.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
    
    # Create feature vector
    feature_vector = feature_eng.create_feature_vector(test_event)
    print(f"\nFeature Vector Shape: {feature_vector.shape}")
    print(f"Feature Vector: {feature_vector}")

if __name__ == "__main__":
    main()