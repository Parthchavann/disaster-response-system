"""
Real data source integrations for the disaster response system.
Integrates with Twitter, News APIs, Weather APIs, and government data sources.
"""

import asyncio
import aiohttp
import tweepy
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
import hashlib
import time
from abc import ABC, abstractmethod

from configs.config import get_config

logger = logging.getLogger(__name__)
config = get_config()


@dataclass
class DataEvent:
    """Standard data event structure"""
    event_id: str
    source: str
    event_type: str
    data: Dict[str, Any]
    location: Optional[Dict[str, float]]
    timestamp: datetime
    confidence: float = 0.0
    raw_data: Optional[Dict[str, Any]] = None


class DataSourceInterface(ABC):
    """Abstract interface for data sources"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the data source"""
        pass
    
    @abstractmethod
    async def fetch_data(self, **kwargs) -> AsyncGenerator[DataEvent, None]:
        """Fetch data from the source"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close connections and cleanup"""
        pass


class TwitterDataSource(DataSourceInterface):
    """Twitter/X data source integration"""
    
    def __init__(self):
        self.api = None
        self.session = None
        self.disaster_keywords = [
            "earthquake", "flood", "wildfire", "hurricane", "tornado", 
            "tsunami", "volcano", "landslide", "emergency", "evacuation",
            "disaster", "crisis", "storm", "fire", "quake"
        ]
    
    async def initialize(self) -> bool:
        """Initialize Twitter API client"""
        try:
            api_config = config.external_apis
            
            if not all([
                api_config.twitter_api_key,
                api_config.twitter_api_secret,
                api_config.twitter_access_token,
                api_config.twitter_access_token_secret
            ]):
                logger.warning("Twitter API credentials not configured, using mock data")
                return False
            
            # Initialize Tweepy client
            auth = tweepy.OAuthHandler(
                api_config.twitter_api_key,
                api_config.twitter_api_secret
            )
            auth.set_access_token(
                api_config.twitter_access_token,
                api_config.twitter_access_token_secret
            )
            
            self.api = tweepy.API(auth, wait_on_rate_limit=True)
            
            # Test connection
            self.api.verify_credentials()
            logger.info("Twitter API initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {e}")
            return False
    
    async def fetch_data(self, **kwargs) -> AsyncGenerator[DataEvent, None]:
        """Fetch tweets related to disasters"""
        try:
            if not self.api:
                # Generate mock data if API not available
                async for event in self._generate_mock_twitter_data():
                    yield event
                return
            
            # Search for disaster-related tweets
            for keyword in self.disaster_keywords:
                try:
                    tweets = tweepy.Cursor(
                        self.api.search_tweets,
                        q=f"{keyword} -RT",  # Exclude retweets
                        lang="en",
                        result_type="recent",
                        count=100
                    ).items(50)
                    
                    for tweet in tweets:
                        event = self._process_tweet(tweet)
                        if event:
                            yield event
                            
                    # Rate limiting delay
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error fetching tweets for keyword '{keyword}': {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in Twitter data fetch: {e}")
    
    def _process_tweet(self, tweet) -> Optional[DataEvent]:
        """Process a tweet into a DataEvent"""
        try:
            # Extract location if available
            location = None
            if tweet.coordinates:
                location = {
                    "latitude": tweet.coordinates.coordinates[1],
                    "longitude": tweet.coordinates.coordinates[0]
                }
            elif tweet.place and tweet.place.bounding_box:
                # Use center of bounding box
                coords = tweet.place.bounding_box.coordinates[0]
                avg_lat = sum(coord[1] for coord in coords) / len(coords)
                avg_lon = sum(coord[0] for coord in coords) / len(coords)
                location = {"latitude": avg_lat, "longitude": avg_lon}
            
            # Generate event ID
            event_id = hashlib.md5(f"twitter_{tweet.id}".encode()).hexdigest()
            
            event = DataEvent(
                event_id=event_id,
                source="twitter",
                event_type="social_media",
                data={
                    "text": tweet.text,
                    "user": tweet.user.screen_name,
                    "followers_count": tweet.user.followers_count,
                    "retweet_count": tweet.retweet_count,
                    "favorite_count": tweet.favorite_count,
                    "verified": tweet.user.verified
                },
                location=location,
                timestamp=tweet.created_at,
                confidence=self._calculate_tweet_confidence(tweet),
                raw_data=tweet._json
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error processing tweet: {e}")
            return None
    
    def _calculate_tweet_confidence(self, tweet) -> float:
        """Calculate confidence score for a tweet"""
        confidence = 0.5  # Base confidence
        
        # Verified user increases confidence
        if tweet.user.verified:
            confidence += 0.2
        
        # High engagement increases confidence
        engagement = tweet.retweet_count + tweet.favorite_count
        if engagement > 100:
            confidence += 0.2
        elif engagement > 10:
            confidence += 0.1
        
        # High follower count increases confidence
        if tweet.user.followers_count > 10000:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def _generate_mock_twitter_data(self) -> AsyncGenerator[DataEvent, None]:
        """Generate mock Twitter data for testing"""
        mock_tweets = [
            {
                "text": "URGENT: Flash flood warning issued for downtown area. Evacuate immediately! #FloodAlert",
                "location": {"latitude": 40.7128, "longitude": -74.0060},
                "confidence": 0.9
            },
            {
                "text": "Wildfire spreading rapidly near residential areas. Smoke visible from miles away.",
                "location": {"latitude": 34.0522, "longitude": -118.2437},
                "confidence": 0.8
            },
            {
                "text": "Earthquake felt across the city! Buildings shaking, please stay safe everyone.",
                "location": {"latitude": 37.7749, "longitude": -122.4194},
                "confidence": 0.85
            }
        ]
        
        for i, tweet_data in enumerate(mock_tweets):
            event_id = hashlib.md5(f"mock_twitter_{i}_{time.time()}".encode()).hexdigest()
            
            yield DataEvent(
                event_id=event_id,
                source="twitter_mock",
                event_type="social_media",
                data={
                    "text": tweet_data["text"],
                    "user": f"mock_user_{i}",
                    "followers_count": 5000,
                    "retweet_count": 50,
                    "favorite_count": 100,
                    "verified": True
                },
                location=tweet_data["location"],
                timestamp=datetime.now(),
                confidence=tweet_data["confidence"]
            )
    
    async def close(self):
        """Close Twitter connections"""
        self.api = None


class NewsDataSource(DataSourceInterface):
    """News API data source integration"""
    
    def __init__(self):
        self.session = None
        self.api_key = None
        self.base_url = None
    
    async def initialize(self) -> bool:
        """Initialize News API client"""
        try:
            api_config = config.external_apis
            self.api_key = api_config.news_api_key
            self.base_url = api_config.news_api_url
            
            if not self.api_key:
                logger.warning("News API key not configured, using mock data")
                return False
            
            self.session = aiohttp.ClientSession()
            
            # Test API connection
            async with self.session.get(
                f"{self.base_url}/top-headlines",
                params={"apiKey": self.api_key, "pageSize": 1}
            ) as response:
                if response.status == 200:
                    logger.info("News API initialized successfully")
                    return True
                else:
                    logger.error(f"News API test failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to initialize News API: {e}")
            return False
    
    async def fetch_data(self, **kwargs) -> AsyncGenerator[DataEvent, None]:
        """Fetch news articles related to disasters"""
        try:
            if not self.session or not self.api_key:
                # Generate mock data if API not available
                async for event in self._generate_mock_news_data():
                    yield event
                return
            
            disaster_queries = [
                "earthquake", "flood", "wildfire", "hurricane", "tornado",
                "natural disaster", "emergency", "evacuation"
            ]
            
            for query in disaster_queries:
                try:
                    params = {
                        "q": query,
                        "apiKey": self.api_key,
                        "pageSize": 20,
                        "language": "en",
                        "sortBy": "publishedAt"
                    }
                    
                    async with self.session.get(
                        f"{self.base_url}/everything",
                        params=params
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            
                            for article in data.get("articles", []):
                                event = self._process_article(article)
                                if event:
                                    yield event
                        else:
                            logger.warning(f"News API request failed: {response.status}")
                    
                    # Rate limiting delay
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error fetching news for query '{query}': {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in News data fetch: {e}")
    
    def _process_article(self, article: Dict[str, Any]) -> Optional[DataEvent]:
        """Process a news article into a DataEvent"""
        try:
            # Generate event ID
            event_id = hashlib.md5(f"news_{article.get('url', '')}".encode()).hexdigest()
            
            event = DataEvent(
                event_id=event_id,
                source="news_api",
                event_type="news",
                data={
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "content": article.get("content", ""),
                    "url": article.get("url", ""),
                    "source_name": article.get("source", {}).get("name", ""),
                    "author": article.get("author", "")
                },
                location=None,  # News articles rarely have precise locations
                timestamp=datetime.fromisoformat(
                    article.get("publishedAt", "").replace("Z", "+00:00")
                ) if article.get("publishedAt") else datetime.now(),
                confidence=self._calculate_news_confidence(article)
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error processing news article: {e}")
            return None
    
    def _calculate_news_confidence(self, article: Dict[str, Any]) -> float:
        """Calculate confidence score for a news article"""
        confidence = 0.7  # Base confidence for news sources
        
        # Reputable sources increase confidence
        source_name = article.get("source", {}).get("name", "").lower()
        reputable_sources = ["reuters", "ap", "bbc", "cnn", "npr", "guardian"]
        
        if any(source in source_name for source in reputable_sources):
            confidence += 0.2
        
        # Recent articles are more relevant
        if article.get("publishedAt"):
            try:
                pub_date = datetime.fromisoformat(
                    article["publishedAt"].replace("Z", "+00:00")
                )
                age_hours = (datetime.now(pub_date.tzinfo) - pub_date).total_seconds() / 3600
                
                if age_hours < 6:
                    confidence += 0.1
                elif age_hours < 24:
                    confidence += 0.05
            except:
                pass
        
        return min(confidence, 1.0)
    
    async def _generate_mock_news_data(self) -> AsyncGenerator[DataEvent, None]:
        """Generate mock news data for testing"""
        mock_articles = [
            {
                "title": "Major Earthquake Strikes California Coast",
                "description": "A magnitude 6.8 earthquake hit the California coast early this morning...",
                "confidence": 0.9
            },
            {
                "title": "Wildfire Forces Evacuations in Colorado",
                "description": "Thousands evacuated as wildfire spreads rapidly through residential areas...",
                "confidence": 0.85
            },
            {
                "title": "Hurricane Warning Issued for Gulf Coast",
                "description": "Category 3 hurricane approaching, residents urged to evacuate...",
                "confidence": 0.9
            }
        ]
        
        for i, article_data in enumerate(mock_articles):
            event_id = hashlib.md5(f"mock_news_{i}_{time.time()}".encode()).hexdigest()
            
            yield DataEvent(
                event_id=event_id,
                source="news_mock",
                event_type="news",
                data={
                    "title": article_data["title"],
                    "description": article_data["description"],
                    "url": f"https://example.com/article_{i}",
                    "source_name": "Mock News",
                    "author": "Mock Reporter"
                },
                location=None,
                timestamp=datetime.now(),
                confidence=article_data["confidence"]
            )
    
    async def close(self):
        """Close News API connections"""
        if self.session:
            await self.session.close()


class WeatherDataSource(DataSourceInterface):
    """Weather API data source integration"""
    
    def __init__(self):
        self.session = None
        self.api_key = None
        self.base_url = None
    
    async def initialize(self) -> bool:
        """Initialize Weather API client"""
        try:
            api_config = config.external_apis
            self.api_key = api_config.weather_api_key
            self.base_url = api_config.weather_api_url
            
            if not self.api_key:
                logger.warning("Weather API key not configured, using mock data")
                return False
            
            self.session = aiohttp.ClientSession()
            logger.info("Weather API initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Weather API: {e}")
            return False
    
    async def fetch_data(self, locations: List[Dict[str, float]] = None, **kwargs) -> AsyncGenerator[DataEvent, None]:
        """Fetch weather data for specific locations"""
        try:
            if not self.session or not self.api_key:
                # Generate mock data if API not available
                async for event in self._generate_mock_weather_data():
                    yield event
                return
            
            # Default locations if none provided
            if not locations:
                locations = [
                    {"latitude": 40.7128, "longitude": -74.0060, "name": "New York"},
                    {"latitude": 34.0522, "longitude": -118.2437, "name": "Los Angeles"},
                    {"latitude": 25.7617, "longitude": -80.1918, "name": "Miami"},
                    {"latitude": 29.7604, "longitude": -95.3698, "name": "Houston"}
                ]
            
            for location in locations:
                try:
                    params = {
                        "lat": location["latitude"],
                        "lon": location["longitude"],
                        "appid": self.api_key,
                        "units": "metric"
                    }
                    
                    async with self.session.get(
                        f"{self.base_url}/weather",
                        params=params
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            event = self._process_weather_data(data, location)
                            if event:
                                yield event
                        else:
                            logger.warning(f"Weather API request failed: {response.status}")
                    
                    # Rate limiting delay
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error fetching weather for location {location}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in Weather data fetch: {e}")
    
    def _process_weather_data(self, data: Dict[str, Any], location: Dict[str, float]) -> Optional[DataEvent]:
        """Process weather data into a DataEvent"""
        try:
            # Generate event ID
            event_id = hashlib.md5(f"weather_{location['latitude']}_{location['longitude']}_{time.time()}".encode()).hexdigest()
            
            weather_data = {
                "temperature": data.get("main", {}).get("temp", 0),
                "humidity": data.get("main", {}).get("humidity", 0),
                "pressure": data.get("main", {}).get("pressure", 1013),
                "wind_speed": data.get("wind", {}).get("speed", 0) * 3.6,  # Convert m/s to km/h
                "wind_direction": data.get("wind", {}).get("deg", 0),
                "visibility": data.get("visibility", 10000) / 1000,  # Convert to km
                "weather_condition": data.get("weather", [{}])[0].get("main", ""),
                "description": data.get("weather", [{}])[0].get("description", ""),
                "city_name": data.get("name", location.get("name", "Unknown"))
            }
            
            # Check for extreme weather conditions
            extreme_conditions = self._check_extreme_weather(weather_data)
            
            event = DataEvent(
                event_id=event_id,
                source="weather_api",
                event_type="weather",
                data=weather_data,
                location={
                    "latitude": location["latitude"],
                    "longitude": location["longitude"]
                },
                timestamp=datetime.now(),
                confidence=0.95 if extreme_conditions else 0.5,  # High confidence for extreme weather
                raw_data=data
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error processing weather data: {e}")
            return None
    
    def _check_extreme_weather(self, weather_data: Dict[str, Any]) -> bool:
        """Check if weather conditions are extreme"""
        # Define extreme weather thresholds
        extreme_conditions = [
            weather_data.get("wind_speed", 0) > 75,  # High wind speed
            weather_data.get("pressure", 1013) < 970,  # Very low pressure
            weather_data.get("temperature", 0) > 40 or weather_data.get("temperature", 0) < -20,  # Extreme temperatures
            weather_data.get("weather_condition", "").lower() in ["thunderstorm", "tornado", "hurricane"]
        ]
        
        return any(extreme_conditions)
    
    async def _generate_mock_weather_data(self) -> AsyncGenerator[DataEvent, None]:
        """Generate mock weather data for testing"""
        mock_weather = [
            {
                "location": {"latitude": 40.7128, "longitude": -74.0060, "name": "New York"},
                "data": {
                    "temperature": 25,
                    "humidity": 60,
                    "pressure": 1013,
                    "wind_speed": 15,
                    "weather_condition": "Clear",
                    "city_name": "New York"
                },
                "confidence": 0.5
            },
            {
                "location": {"latitude": 25.7617, "longitude": -80.1918, "name": "Miami"},
                "data": {
                    "temperature": 35,
                    "humidity": 85,
                    "pressure": 950,
                    "wind_speed": 120,
                    "weather_condition": "Hurricane",
                    "city_name": "Miami"
                },
                "confidence": 0.95
            }
        ]
        
        for i, weather_info in enumerate(mock_weather):
            event_id = hashlib.md5(f"mock_weather_{i}_{time.time()}".encode()).hexdigest()
            
            yield DataEvent(
                event_id=event_id,
                source="weather_mock",
                event_type="weather",
                data=weather_info["data"],
                location=weather_info["location"],
                timestamp=datetime.now(),
                confidence=weather_info["confidence"]
            )
    
    async def close(self):
        """Close Weather API connections"""
        if self.session:
            await self.session.close()


class RealDataIntegrator:
    """Main class to coordinate all real data sources"""
    
    def __init__(self):
        self.sources: Dict[str, DataSourceInterface] = {
            "twitter": TwitterDataSource(),
            "news": NewsDataSource(),
            "weather": WeatherDataSource()
        }
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize all data sources"""
        try:
            initialized_sources = []
            
            for name, source in self.sources.items():
                try:
                    success = await source.initialize()
                    if success:
                        initialized_sources.append(name)
                        logger.info(f"Data source '{name}' initialized successfully")
                    else:
                        logger.warning(f"Data source '{name}' failed to initialize, will use mock data")
                except Exception as e:
                    logger.error(f"Error initializing data source '{name}': {e}")
            
            self.initialized = True
            logger.info(f"Data integrator initialized with {len(initialized_sources)} sources: {initialized_sources}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize data integrator: {e}")
            return False
    
    async def fetch_all_data(self, **kwargs) -> AsyncGenerator[DataEvent, None]:
        """Fetch data from all sources"""
        if not self.initialized:
            await self.initialize()
        
        # Create tasks for all data sources
        tasks = []
        for name, source in self.sources.items():
            task = asyncio.create_task(self._fetch_source_data(name, source, **kwargs))
            tasks.append(task)
        
        # Yield events as they come from any source
        async for event in self._merge_async_generators(tasks):
            yield event
    
    async def _fetch_source_data(self, name: str, source: DataSourceInterface, **kwargs):
        """Fetch data from a single source"""
        try:
            async for event in source.fetch_data(**kwargs):
                yield event
        except Exception as e:
            logger.error(f"Error fetching data from source '{name}': {e}")
    
    async def _merge_async_generators(self, tasks: List[asyncio.Task]):
        """Merge multiple async generators into one"""
        pending = set(tasks)
        
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            
            for task in done:
                try:
                    async for event in task.result():
                        yield event
                except Exception as e:
                    logger.error(f"Error in async generator task: {e}")
    
    async def close(self):
        """Close all data source connections"""
        for source in self.sources.values():
            try:
                await source.close()
            except Exception as e:
                logger.error(f"Error closing data source: {e}")


# Example usage and testing
async def main():
    """Test the real data integrator"""
    integrator = RealDataIntegrator()
    
    try:
        await integrator.initialize()
        
        logger.info("Starting data fetch...")
        event_count = 0
        
        async for event in integrator.fetch_all_data():
            logger.info(f"Received event: {event.source} - {event.event_type} - {event.confidence}")
            event_count += 1
            
            if event_count >= 10:  # Limit for testing
                break
        
        logger.info(f"Fetched {event_count} events total")
        
    finally:
        await integrator.close()


if __name__ == "__main__":
    asyncio.run(main())