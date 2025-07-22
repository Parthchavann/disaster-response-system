"""
Configuration management for the disaster response system.
Handles loading environment-specific configurations.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration"""
    redis_host: str
    redis_port: int
    redis_db: int
    redis_password: Optional[str]
    qdrant_host: str
    qdrant_port: int
    qdrant_api_key: Optional[str]
    qdrant_collection_name: str


@dataclass
class KafkaConfig:
    """Kafka configuration"""
    bootstrap_servers: str
    topics: list
    group_id: str
    auto_offset_reset: str
    security_protocol: Optional[str] = None
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None


@dataclass
class AuthConfig:
    """Authentication configuration"""
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int


@dataclass
class APIConfig:
    """API configuration"""
    host: str
    port: int
    workers: int
    debug: bool
    cors_origins: list
    allowed_hosts: list


@dataclass
class MLConfig:
    """Machine learning configuration"""
    model_cache_dir: str
    text_model_name: str
    image_model_name: str
    embedding_model_name: str
    max_workers: int
    batch_size: int
    prediction_timeout: int


@dataclass
class ExternalAPIConfig:
    """External API configuration"""
    weather_api_key: Optional[str]
    weather_api_url: str
    twitter_api_key: Optional[str]
    twitter_api_secret: Optional[str]
    twitter_access_token: Optional[str]
    twitter_access_token_secret: Optional[str]
    news_api_key: Optional[str]
    news_api_url: str


@dataclass
class MonitoringConfig:
    """Monitoring configuration"""
    prometheus_port: int
    grafana_port: int
    enable_metrics: bool
    log_level: str
    log_format: str
    log_file: str


class ConfigManager:
    """Configuration manager for the disaster response system"""
    
    def __init__(self, environment: Optional[str] = None):
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment file"""
        config_dir = Path(__file__).parent
        env_file = config_dir / f"{self.environment}.env"
        
        if env_file.exists():
            self._load_env_file(env_file)
        else:
            logger.warning(f"Configuration file {env_file} not found, using environment variables")
        
        # Override with actual environment variables
        self._load_from_env()
    
    def _load_env_file(self, env_file: Path):
        """Load configuration from .env file"""
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self._config[key.strip()] = value.strip()
        except Exception as e:
            logger.error(f"Error loading config file {env_file}: {e}")
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        for key, value in os.environ.items():
            self._config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        value = self._config.get(key, default)
        
        # Type conversion
        if isinstance(value, str):
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            if value.isdigit():
                return int(value)
            if ',' in value:
                return [item.strip() for item in value.split(',')]
        
        return value
    
    @property
    def database(self) -> DatabaseConfig:
        """Get database configuration"""
        return DatabaseConfig(
            redis_host=self.get("REDIS_HOST", "localhost"),
            redis_port=self.get("REDIS_PORT", 6379),
            redis_db=self.get("REDIS_DB", 0),
            redis_password=self.get("REDIS_PASSWORD"),
            qdrant_host=self.get("QDRANT_HOST", "localhost"),
            qdrant_port=self.get("QDRANT_PORT", 6333),
            qdrant_api_key=self.get("QDRANT_API_KEY"),
            qdrant_collection_name=self.get("QDRANT_COLLECTION_NAME", "disaster_events")
        )
    
    @property
    def kafka(self) -> KafkaConfig:
        """Get Kafka configuration"""
        topics = self.get("KAFKA_TOPICS", ["disaster.social.text", "disaster.social.images", "disaster.weather.sensors", "disaster.satellite.data"])
        if isinstance(topics, str):
            topics = [topic.strip() for topic in topics.split(',')]
        
        return KafkaConfig(
            bootstrap_servers=self.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            topics=topics,
            group_id=self.get("KAFKA_GROUP_ID", "disaster-response-consumer"),
            auto_offset_reset=self.get("KAFKA_AUTO_OFFSET_RESET", "latest"),
            security_protocol=self.get("KAFKA_SECURITY_PROTOCOL"),
            sasl_mechanism=self.get("KAFKA_SASL_MECHANISM"),
            sasl_username=self.get("KAFKA_SASL_USERNAME"),
            sasl_password=self.get("KAFKA_SASL_PASSWORD")
        )
    
    @property
    def auth(self) -> AuthConfig:
        """Get authentication configuration"""
        return AuthConfig(
            jwt_secret_key=self.get("JWT_SECRET_KEY", "change-me-in-production"),
            jwt_algorithm=self.get("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=self.get("ACCESS_TOKEN_EXPIRE_MINUTES", 30),
            refresh_token_expire_days=self.get("REFRESH_TOKEN_EXPIRE_DAYS", 7)
        )
    
    @property
    def api(self) -> APIConfig:
        """Get API configuration"""
        cors_origins = self.get("CORS_ORIGINS", ["*"])
        allowed_hosts = self.get("ALLOWED_HOSTS", ["*"])
        
        return APIConfig(
            host=self.get("API_HOST", "0.0.0.0"),
            port=self.get("API_PORT", 8000),
            workers=self.get("API_WORKERS", 1),
            debug=self.get("DEBUG", False),
            cors_origins=cors_origins,
            allowed_hosts=allowed_hosts
        )
    
    @property
    def ml(self) -> MLConfig:
        """Get ML configuration"""
        return MLConfig(
            model_cache_dir=self.get("MODEL_CACHE_DIR", "./trained_models"),
            text_model_name=self.get("TEXT_MODEL_NAME", "distilbert-base-uncased"),
            image_model_name=self.get("IMAGE_MODEL_NAME", "resnet50"),
            embedding_model_name=self.get("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"),
            max_workers=self.get("MAX_WORKERS", 4),
            batch_size=self.get("BATCH_SIZE", 32),
            prediction_timeout=self.get("PREDICTION_TIMEOUT", 30)
        )
    
    @property
    def external_apis(self) -> ExternalAPIConfig:
        """Get external API configuration"""
        return ExternalAPIConfig(
            weather_api_key=self.get("WEATHER_API_KEY"),
            weather_api_url=self.get("WEATHER_API_URL", "https://api.openweathermap.org/data/2.5"),
            twitter_api_key=self.get("TWITTER_API_KEY"),
            twitter_api_secret=self.get("TWITTER_API_SECRET"),
            twitter_access_token=self.get("TWITTER_ACCESS_TOKEN"),
            twitter_access_token_secret=self.get("TWITTER_ACCESS_TOKEN_SECRET"),
            news_api_key=self.get("NEWS_API_KEY"),
            news_api_url=self.get("NEWS_API_URL", "https://newsapi.org/v2")
        )
    
    @property
    def monitoring(self) -> MonitoringConfig:
        """Get monitoring configuration"""
        return MonitoringConfig(
            prometheus_port=self.get("PROMETHEUS_PORT", 9090),
            grafana_port=self.get("GRAFANA_PORT", 3000),
            enable_metrics=self.get("ENABLE_METRICS", True),
            log_level=self.get("LOG_LEVEL", "INFO"),
            log_format=self.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            log_file=self.get("LOG_FILE", "logs/disaster-response.log")
        )
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment == "development"
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment == "production"
    
    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.environment == "testing"


# Global configuration instance
config = ConfigManager()


def get_config() -> ConfigManager:
    """Get the global configuration instance"""
    return config


def reload_config(environment: Optional[str] = None):
    """Reload configuration with optional environment override"""
    global config
    config = ConfigManager(environment)
    return config