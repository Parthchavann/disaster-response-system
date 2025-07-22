"""
Apache Spark Streaming Consumer for real-time disaster data processing
Processes Kafka streams and performs initial data transformation
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DisasterStreamProcessor:
    """Real-time stream processor for disaster data using Spark Structured Streaming"""
    
    def __init__(self, kafka_servers="localhost:9092"):
        self.kafka_servers = kafka_servers
        self.spark = None
        self.init_spark_session()
        
    def init_spark_session(self):
        """Initialize Spark session with required configurations"""
        self.spark = SparkSession.builder \
            .appName("DisasterResponseStreaming") \
            .config("spark.jars.packages", 
                   "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel("WARN")
        logger.info("Spark session initialized")
    
    def define_schemas(self):
        """Define schemas for different data sources"""
        
        # Base disaster event schema
        base_event_schema = StructType([
            StructField("event_id", StringType(), True),
            StructField("timestamp", StringType(), True),
            StructField("event_type", StringType(), True),
            StructField("location", StructType([
                StructField("lat", DoubleType(), True),
                StructField("lon", DoubleType(), True),
                StructField("city", StringType(), True)
            ]), True),
            StructField("severity", StringType(), True),
            StructField("confidence", DoubleType(), True),
            StructField("source", StringType(), True)
        ])
        
        # Social media text data schema
        social_text_schema = StructType([
            StructField("text", StringType(), True),
            StructField("user_id", StringType(), True),
            StructField("platform", StringType(), True),
            StructField("disaster_type", StringType(), True)
        ])
        
        # Social media image data schema
        social_image_schema = StructType([
            StructField("image_data", StringType(), True),
            StructField("description", StringType(), True),
            StructField("user_id", StringType(), True),
            StructField("platform", StringType(), True),
            StructField("disaster_type", StringType(), True)
        ])
        
        # Weather sensor data schema
        weather_schema = StructType([
            StructField("sensor_id", StringType(), True),
            StructField("wind_speed_mph", DoubleType(), True),
            StructField("precipitation_mm", DoubleType(), True),
            StructField("temperature_c", DoubleType(), True),
            StructField("pressure_hpa", DoubleType(), True),
            StructField("humidity_percent", DoubleType(), True),
            StructField("is_extreme", BooleanType(), True)
        ])
        
        # Satellite data schema
        satellite_schema = StructType([
            StructField("satellite_id", StringType(), True),
            StructField("observation_type", StringType(), True),
            StructField("resolution_m", IntegerType(), True),
            StructField("cloud_cover_percent", DoubleType(), True),
            StructField("has_anomaly", BooleanType(), True),
            StructField("anomaly_type", StringType(), True),
            StructField("confidence_score", DoubleType(), True)
        ])
        
        return {
            'base_event': base_event_schema,
            'social_text': social_text_schema,
            'social_image': social_image_schema,
            'weather': weather_schema,
            'satellite': satellite_schema
        }
    
    def read_kafka_stream(self, topic: str):
        """Read streaming data from Kafka topic"""
        return self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", self.kafka_servers) \
            .option("subscribe", topic) \
            .option("startingOffsets", "latest") \
            .load()
    
    def process_social_media_text(self):
        """Process social media text streams"""
        schemas = self.define_schemas()
        
        # Read from Kafka
        raw_stream = self.read_kafka_stream("disaster.social.text")
        
        # Parse JSON and extract data
        parsed_stream = raw_stream.select(
            col("key").cast("string").alias("event_id"),
            from_json(col("value").cast("string"), 
                     StructType([
                         StructField("event_id", StringType()),
                         StructField("timestamp", StringType()),
                         StructField("event_type", StringType()),
                         StructField("location", schemas['base_event']['location'].dataType),
                         StructField("severity", StringType()),
                         StructField("confidence", DoubleType()),
                         StructField("source", StringType()),
                         StructField("data", schemas['social_text'])
                     ])).alias("event"),
            col("timestamp").alias("kafka_timestamp")
        )
        
        # Flatten and transform data
        processed_stream = parsed_stream.select(
            col("event.event_id"),
            col("event.timestamp").cast("timestamp"),
            col("event.event_type"),
            col("event.location.lat").alias("latitude"),
            col("event.location.lon").alias("longitude"),
            col("event.location.city"),
            col("event.severity"),
            col("event.confidence"),
            col("event.source"),
            col("event.data.text"),
            col("event.data.user_id"),
            col("event.data.platform"),
            col("event.data.disaster_type"),
            length(col("event.data.text")).alias("text_length"),
            when(col("event.data.text").rlike("(?i)(urgent|emergency|help|911)"), True)
                .otherwise(False).alias("is_urgent"),
            kafka_timestamp
        )
        
        return processed_stream
    
    def process_weather_sensors(self):
        """Process weather sensor streams"""
        schemas = self.define_schemas()
        
        raw_stream = self.read_kafka_stream("disaster.weather.sensors")
        
        parsed_stream = raw_stream.select(
            from_json(col("value").cast("string"), 
                     StructType([
                         StructField("event_id", StringType()),
                         StructField("timestamp", StringType()),
                         StructField("event_type", StringType()),
                         StructField("location", schemas['base_event']['location'].dataType),
                         StructField("severity", StringType()),
                         StructField("confidence", DoubleType()),
                         StructField("source", StringType()),
                         StructField("data", schemas['weather'])
                     ])).alias("event"),
            col("timestamp").alias("kafka_timestamp")
        )
        
        # Add weather risk scoring
        processed_stream = parsed_stream.select(
            col("event.event_id"),
            col("event.timestamp").cast("timestamp"),
            col("event.location.lat").alias("latitude"),
            col("event.location.lon").alias("longitude"),
            col("event.data.sensor_id"),
            col("event.data.wind_speed_mph"),
            col("event.data.precipitation_mm"),
            col("event.data.temperature_c"),
            col("event.data.pressure_hpa"),
            col("event.data.humidity_percent"),
            col("event.data.is_extreme"),
            # Weather risk score calculation
            when(col("event.data.wind_speed_mph") > 75, 0.8)
                .when(col("event.data.precipitation_mm") > 25, 0.7)
                .when(col("event.data.pressure_hpa") < 970, 0.6)
                .otherwise(0.2).alias("weather_risk_score"),
            kafka_timestamp
        )
        
        return processed_stream
    
    def process_satellite_data(self):
        """Process satellite data streams"""
        schemas = self.define_schemas()
        
        raw_stream = self.read_kafka_stream("disaster.satellite.data")
        
        parsed_stream = raw_stream.select(
            from_json(col("value").cast("string"), 
                     StructType([
                         StructField("event_id", StringType()),
                         StructField("timestamp", StringType()),
                         StructField("event_type", StringType()),
                         StructField("location", schemas['base_event']['location'].dataType),
                         StructField("severity", StringType()),
                         StructField("confidence", DoubleType()),
                         StructField("source", StringType()),
                         StructField("data", schemas['satellite'])
                     ])).alias("event"),
            col("timestamp").alias("kafka_timestamp")
        )
        
        processed_stream = parsed_stream.select(
            col("event.event_id"),
            col("event.timestamp").cast("timestamp"),
            col("event.location.lat").alias("latitude"),
            col("event.location.lon").alias("longitude"),
            col("event.data.satellite_id"),
            col("event.data.observation_type"),
            col("event.data.resolution_m"),
            col("event.data.cloud_cover_percent"),
            col("event.data.has_anomaly"),
            col("event.data.anomaly_type"),
            col("event.data.confidence_score"),
            # Satellite observation quality score
            when(col("event.data.cloud_cover_percent") < 20, 0.9)
                .when(col("event.data.cloud_cover_percent") < 50, 0.7)
                .otherwise(0.4).alias("observation_quality"),
            kafka_timestamp
        )
        
        return processed_stream
    
    def aggregate_disaster_events(self):
        """Create real-time aggregations for disaster monitoring"""
        
        # Process all streams
        social_stream = self.process_social_media_text()
        weather_stream = self.process_weather_sensors()
        satellite_stream = self.process_satellite_data()
        
        # Geographic aggregations (5-minute windows)
        geographic_agg = social_stream.filter(col("is_urgent") == True) \
            .withWatermark("timestamp", "10 minutes") \
            .groupBy(
                window(col("timestamp"), "5 minutes"),
                col("disaster_type"),
                expr("round(latitude, 1)").alias("lat_bin"),
                expr("round(longitude, 1)").alias("lon_bin")
            ) \
            .agg(
                count("*").alias("urgent_reports"),
                avg("confidence").alias("avg_confidence"),
                collect_list("text").alias("sample_texts")
            )
        
        # Weather risk aggregations
        weather_risk_agg = weather_stream.filter(col("weather_risk_score") > 0.5) \
            .withWatermark("timestamp", "10 minutes") \
            .groupBy(
                window(col("timestamp"), "10 minutes"),
                expr("round(latitude, 1)").alias("lat_bin"),
                expr("round(longitude, 1)").alias("lon_bin")
            ) \
            .agg(
                max("weather_risk_score").alias("max_risk_score"),
                avg("wind_speed_mph").alias("avg_wind_speed"),
                avg("precipitation_mm").alias("avg_precipitation")
            )
        
        return geographic_agg, weather_risk_agg
    
    def write_to_console(self, stream, query_name: str):
        """Write stream to console for monitoring"""
        return stream.writeStream \
            .outputMode("update") \
            .format("console") \
            .option("truncate", False) \
            .queryName(query_name) \
            .trigger(processingTime="30 seconds") \
            .start()
    
    def write_to_delta(self, stream, path: str, query_name: str):
        """Write stream to Delta Lake for storage"""
        return stream.writeStream \
            .outputMode("append") \
            .format("delta") \
            .option("path", path) \
            .option("checkpointLocation", f"{path}/_checkpoints/{query_name}") \
            .queryName(query_name) \
            .trigger(processingTime="1 minute") \
            .start()
    
    def run_streaming_pipeline(self):
        """Run the complete streaming pipeline"""
        logger.info("Starting disaster response streaming pipeline")
        
        # Create aggregated streams
        geographic_agg, weather_risk_agg = self.aggregate_disaster_events()
        
        # Start console output queries for monitoring
        geo_console_query = self.write_to_console(geographic_agg, "geographic_alerts")
        weather_console_query = self.write_to_console(weather_risk_agg, "weather_alerts")
        
        # Start Delta Lake storage queries (uncomment when Delta Lake is available)
        # geo_delta_query = self.write_to_delta(
        #     geographic_agg, "/tmp/delta/geographic_alerts", "geo_delta_sink"
        # )
        # weather_delta_query = self.write_to_delta(
        #     weather_risk_agg, "/tmp/delta/weather_alerts", "weather_delta_sink"
        # )
        
        try:
            # Wait for queries to complete
            self.spark.streams.awaitAnyTermination()
        except KeyboardInterrupt:
            logger.info("Stopping streaming pipeline...")
        finally:
            # Stop all queries
            for query in self.spark.streams.active:
                query.stop()
            self.spark.stop()
            logger.info("Streaming pipeline stopped")

if __name__ == "__main__":
    processor = DisasterStreamProcessor()
    processor.run_streaming_pipeline()