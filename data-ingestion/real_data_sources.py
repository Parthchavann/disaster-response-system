#!/usr/bin/env python3
"""
Real Data Source Integrations for Disaster Response System
Connects to actual APIs for Twitter, weather data, news feeds, and USGS
"""

import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Iterator
from dataclasses import dataclass
# import asyncio
# import aiohttp
from urllib.parse import urlencode
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DisasterEvent:
    """Real disaster event data structure"""
    source: str
    event_type: str
    text: str
    location: Dict[str, float]
    timestamp: datetime
    confidence: float
    metadata: Dict
    images: List[str] = None

class TwitterAPIClient:
    """Real Twitter API v2 client for disaster-related tweets"""
    
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.base_url = "https://api.twitter.com/2"
        self.headers = {"Authorization": f"Bearer {bearer_token}"}
        
    def search_disaster_tweets(self, max_results: int = 100) -> List[Dict]:
        """Search for disaster-related tweets using Twitter API v2"""
        
        # Disaster-related keywords and hashtags
        query = (
            "(flood OR flooding OR wildfire OR earthquake OR hurricane OR tornado OR "
            "disaster OR emergency OR evacuation OR #disaster #emergency #flood #fire "
            "#earthquake #hurricane #tornado) "
            "-is:retweet lang:en has:geo"
        )
        
        params = {
            'query': query,
            'max_results': min(max_results, 100),  # API limit
            'tweet.fields': 'created_at,public_metrics,context_annotations,geo,attachments',
            'expansions': 'geo.place_id,attachments.media_keys',
            'place.fields': 'geo,name,country_code',
            'media.fields': 'url,preview_image_url'
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/tweets/search/recent",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                tweets = data.get('data', [])
                places = {place['id']: place for place in data.get('includes', {}).get('places', [])}
                media = {media['media_key']: media for media in data.get('includes', {}).get('media', [])}
                
                processed_tweets = []
                for tweet in tweets:
                    processed_tweet = self._process_tweet(tweet, places, media)
                    if processed_tweet:
                        processed_tweets.append(processed_tweet)
                
                logger.info(f"Retrieved {len(processed_tweets)} disaster-related tweets")
                return processed_tweets
            else:
                logger.error(f"Twitter API error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}")
            return []
    
    def _process_tweet(self, tweet: Dict, places: Dict, media: Dict) -> Optional[Dict]:
        """Process raw tweet data into standardized format"""
        try:
            # Extract location if available
            location = {"latitude": 0.0, "longitude": 0.0}
            
            if tweet.get('geo') and tweet['geo'].get('place_id'):
                place = places.get(tweet['geo']['place_id'])
                if place and place.get('geo'):
                    coords = place['geo'].get('bbox', [])
                    if len(coords) >= 4:
                        # Use center of bounding box
                        location["longitude"] = (coords[0] + coords[2]) / 2
                        location["latitude"] = (coords[1] + coords[3]) / 2
            
            # Extract images if available
            images = []
            if tweet.get('attachments', {}).get('media_keys'):
                for media_key in tweet['attachments']['media_keys']:
                    if media_key in media:
                        media_item = media[media_key]
                        if media_item.get('url'):
                            images.append(media_item['url'])
                        elif media_item.get('preview_image_url'):
                            images.append(media_item['preview_image_url'])
            
            return {
                'id': tweet['id'],
                'text': tweet['text'],
                'created_at': tweet['created_at'],
                'location': location,
                'images': images,
                'metrics': tweet.get('public_metrics', {}),
                'source': 'twitter'
            }
            
        except Exception as e:
            logger.error(f"Error processing tweet: {e}")
            return None

class WeatherAPIClient:
    """Real weather data client using OpenWeatherMap API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5"
        
    def get_severe_weather_alerts(self, locations: List[Dict[str, float]]) -> List[Dict]:
        """Get severe weather alerts for specified locations"""
        alerts = []
        
        for location in locations:
            try:
                # Get current weather and alerts
                params = {
                    'lat': location['latitude'],
                    'lon': location['longitude'],
                    'appid': self.api_key,
                    'units': 'metric'
                }
                
                # Get weather alerts
                response = requests.get(
                    f"{self.base_url}/onecall",
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check for weather alerts
                    if 'alerts' in data:
                        for alert in data['alerts']:
                            alerts.append({
                                'location': location,
                                'event': alert.get('event', ''),
                                'description': alert.get('description', ''),
                                'start': alert.get('start', 0),
                                'end': alert.get('end', 0),
                                'source': 'weather_api'
                            })
                    
                    # Check for severe weather conditions
                    current = data.get('current', {})
                    weather = current.get('weather', [{}])[0]
                    
                    if self._is_severe_weather(current, weather):
                        alerts.append({
                            'location': location,
                            'event': 'severe_weather',
                            'description': f"Severe weather conditions: {weather.get('description', '')}",
                            'weather_data': current,
                            'source': 'weather_api'
                        })
                        
                time.sleep(0.1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error fetching weather data for {location}: {e}")
        
        logger.info(f"Retrieved {len(alerts)} weather alerts")
        return alerts
    
    def _is_severe_weather(self, current: Dict, weather: Dict) -> bool:
        """Determine if weather conditions are severe"""
        weather_id = weather.get('id', 0)
        wind_speed = current.get('wind_speed', 0)
        
        # Severe weather conditions based on OpenWeatherMap codes
        severe_conditions = [
            weather_id >= 200 and weather_id < 300,  # Thunderstorm
            weather_id >= 500 and weather_id < 600,  # Rain (heavy)
            weather_id >= 600 and weather_id < 700,  # Snow
            weather_id >= 700 and weather_id < 800,  # Atmospheric conditions
            wind_speed > 15,  # High wind (>15 m/s)
        ]
        
        return any(severe_conditions)

class USGSEarthquakeClient:
    """Real USGS earthquake data client"""
    
    def __init__(self):
        self.base_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        
    def get_recent_earthquakes(self, min_magnitude: float = 4.0, hours: int = 168) -> List[Dict]:
        """Get recent earthquakes from USGS (default: last week)"""
        
        # Use a longer time period for better results
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        params = {
            'format': 'geojson',
            'starttime': start_time.strftime('%Y-%m-%d'),
            'endtime': end_time.strftime('%Y-%m-%d'),
            'minmagnitude': min_magnitude,
            'orderby': 'time'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                earthquakes = []
                
                for feature in data.get('features', []):
                    props = feature.get('properties', {})
                    coords = feature.get('geometry', {}).get('coordinates', [])
                    
                    if len(coords) >= 2:
                        earthquake = {
                            'id': feature.get('id'),
                            'magnitude': props.get('mag', 0),
                            'place': props.get('place', ''),
                            'time': props.get('time', 0),
                            'location': {
                                'longitude': coords[0],
                                'latitude': coords[1],
                                'depth': coords[2] if len(coords) > 2 else 0
                            },
                            'url': props.get('url', ''),
                            'source': 'usgs'
                        }
                        earthquakes.append(earthquake)
                
                logger.info(f"Retrieved {len(earthquakes)} recent earthquakes")
                return earthquakes
            else:
                logger.error(f"USGS API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching earthquake data: {e}")
            return []

class NewsAPIClient:
    """Real news data client for disaster-related news"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        
    def get_disaster_news(self, max_articles: int = 100) -> List[Dict]:
        """Get disaster-related news articles"""
        
        # Disaster-related keywords
        disaster_keywords = [
            "natural disaster", "earthquake", "flood", "wildfire", "hurricane", 
            "tornado", "emergency", "evacuation", "storm", "tsunami"
        ]
        
        query = " OR ".join(disaster_keywords)
        
        params = {
            'q': query,
            'language': 'en',
            'sortBy': 'publishedAt',
            'pageSize': min(max_articles, 100),
            'apiKey': self.api_key
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/everything",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                
                processed_articles = []
                for article in articles:
                    processed_article = {
                        'title': article.get('title', ''),
                        'description': article.get('description', ''),
                        'content': article.get('content', ''),
                        'url': article.get('url', ''),
                        'published_at': article.get('publishedAt', ''),
                        'source': article.get('source', {}).get('name', ''),
                        'url_to_image': article.get('urlToImage', ''),
                        'source_type': 'news'
                    }
                    processed_articles.append(processed_article)
                
                logger.info(f"Retrieved {len(processed_articles)} disaster-related news articles")
                return processed_articles
            else:
                logger.error(f"News API error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching news data: {e}")
            return []

class RealDataIntegrator:
    """Main class to integrate all real data sources"""
    
    def __init__(self, config: Dict[str, str]):
        """Initialize with API keys and configuration"""
        self.twitter_client = None
        self.weather_client = None
        self.usgs_client = USGSEarthquakeClient()
        self.news_client = None
        
        # Initialize clients if API keys are provided
        if config.get('twitter_bearer_token'):
            self.twitter_client = TwitterAPIClient(config['twitter_bearer_token'])
        
        if config.get('weather_api_key'):
            self.weather_client = WeatherAPIClient(config['weather_api_key'])
        
        if config.get('news_api_key'):
            self.news_client = NewsAPIClient(config['news_api_key'])
        
        # Default monitoring locations (major cities)
        self.monitor_locations = [
            {"latitude": 40.7128, "longitude": -74.0060, "name": "New York"},
            {"latitude": 34.0522, "longitude": -118.2437, "name": "Los Angeles"},
            {"latitude": 41.8781, "longitude": -87.6298, "name": "Chicago"},
            {"latitude": 29.7604, "longitude": -95.3698, "name": "Houston"},
            {"latitude": 25.7617, "longitude": -80.1918, "name": "Miami"},
        ]
    
    def collect_all_data(self) -> List[DisasterEvent]:
        """Collect data from all available sources"""
        all_events = []
        
        # Collect Twitter data
        if self.twitter_client:
            try:
                tweets = self.twitter_client.search_disaster_tweets()
                for tweet in tweets:
                    event = DisasterEvent(
                        source="twitter",
                        event_type="social_media",
                        text=tweet['text'],
                        location=tweet['location'],
                        timestamp=datetime.fromisoformat(tweet['created_at'].replace('Z', '+00:00')),
                        confidence=0.7,  # Base confidence for social media
                        metadata=tweet,
                        images=tweet.get('images', [])
                    )
                    all_events.append(event)
            except Exception as e:
                logger.error(f"Error collecting Twitter data: {e}")
        
        # Collect weather data
        if self.weather_client:
            try:
                weather_alerts = self.weather_client.get_severe_weather_alerts(self.monitor_locations)
                for alert in weather_alerts:
                    event = DisasterEvent(
                        source="weather_api",
                        event_type="weather_alert",
                        text=alert['description'],
                        location=alert['location'],
                        timestamp=datetime.now(),
                        confidence=0.9,  # High confidence for official weather data
                        metadata=alert
                    )
                    all_events.append(event)
            except Exception as e:
                logger.error(f"Error collecting weather data: {e}")
        
        # Collect earthquake data
        try:
            earthquakes = self.usgs_client.get_recent_earthquakes()
            for eq in earthquakes:
                event = DisasterEvent(
                    source="usgs",
                    event_type="earthquake",
                    text=f"Magnitude {eq['magnitude']} earthquake near {eq['place']}",
                    location=eq['location'],
                    timestamp=datetime.fromtimestamp(eq['time'] / 1000),  # USGS uses milliseconds
                    confidence=0.95,  # Very high confidence for USGS data
                    metadata=eq
                )
                all_events.append(event)
        except Exception as e:
            logger.error(f"Error collecting earthquake data: {e}")
        
        # Collect news data
        if self.news_client:
            try:
                news_articles = self.news_client.get_disaster_news()
                for article in news_articles:
                    # Estimate location (would need geocoding service in production)
                    estimated_location = {"latitude": 0.0, "longitude": 0.0}
                    
                    event = DisasterEvent(
                        source="news",
                        event_type="news_report",
                        text=f"{article['title']}. {article['description']}",
                        location=estimated_location,
                        timestamp=datetime.fromisoformat(article['published_at'].replace('Z', '+00:00')),
                        confidence=0.8,  # Good confidence for news sources
                        metadata=article
                    )
                    all_events.append(event)
            except Exception as e:
                logger.error(f"Error collecting news data: {e}")
        
        logger.info(f"Collected {len(all_events)} total events from all sources")
        return all_events
    
    def stream_data(self, interval_seconds: int = 60) -> Iterator[List[DisasterEvent]]:
        """Stream real data continuously"""
        while True:
            try:
                events = self.collect_all_data()
                yield events
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                logger.info("Data streaming stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in data streaming: {e}")
                time.sleep(interval_seconds)

def load_config() -> Dict[str, str]:
    """Load API configuration from environment variables or config file"""
    config = {
        'twitter_bearer_token': os.getenv('TWITTER_BEARER_TOKEN'),
        'weather_api_key': os.getenv('OPENWEATHER_API_KEY'),
        'news_api_key': os.getenv('NEWS_API_KEY'),
    }
    
    # Remove None values
    return {k: v for k, v in config.items() if v is not None}

def main():
    """Demo the real data integration"""
    print("🌐 Real Data Source Integration Demo")
    print("=" * 50)
    
    # Load configuration
    config = load_config()
    
    if not config:
        print("⚠️  No API keys found in environment variables.")
        print("   Set TWITTER_BEARER_TOKEN, OPENWEATHER_API_KEY, NEWS_API_KEY for full functionality")
        print("   Demonstrating with USGS earthquake data only...")
        
    # Initialize integrator
    integrator = RealDataIntegrator(config)
    
    # Collect data
    events = integrator.collect_all_data()
    
    # Display results
    print(f"\n📊 Collected {len(events)} real disaster events:")
    print("-" * 50)
    
    for i, event in enumerate(events[:10], 1):  # Show first 10
        print(f"{i}. [{event.source.upper()}] {event.event_type}")
        print(f"   Text: {event.text[:80]}...")
        print(f"   Location: {event.location['latitude']:.4f}, {event.location['longitude']:.4f}")
        print(f"   Confidence: {event.confidence:.2f}")
        print(f"   Time: {event.timestamp}")
        print()
    
    if len(events) > 10:
        print(f"... and {len(events) - 10} more events")

if __name__ == "__main__":
    main()