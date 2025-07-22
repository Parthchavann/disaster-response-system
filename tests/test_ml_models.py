import pytest
import torch
import numpy as np
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ml_models.text_classifier import DisasterTextClassifier
from ml_models.image_classifier import DisasterImageClassifier
from ml_models.multimodal_fusion import MultimodalFusionModel


class TestDisasterTextClassifier:
    
    def setup_method(self):
        self.classifier = DisasterTextClassifier()
    
    def test_initialization(self):
        assert self.classifier.model_name == "distilbert-base-uncased"
        assert len(self.classifier.disaster_labels) == 7
        assert "flood" in self.classifier.disaster_labels
    
    def test_predict_text(self):
        sample_text = "Emergency flood situation downtown area evacuate immediately"
        result = self.classifier.predict(sample_text)
        
        assert "prediction" in result
        assert "confidence" in result
        assert result["prediction"] in self.classifier.disaster_labels
        assert 0 <= result["confidence"] <= 1
    
    def test_extract_features(self):
        text = "URGENT: Wildfire spreading rapidly near residential areas!"
        features = self.classifier.extract_features(text)
        
        assert len(features) == 5
        assert features[0] == len(text)  # text_length
        assert features[1] > 0  # urgency_score
        assert features[2] > 0  # disaster_keyword_count
        assert features[4] > 0  # caps_ratio


class TestDisasterImageClassifier:
    
    def setup_method(self):
        self.classifier = DisasterImageClassifier()
    
    def test_initialization(self):
        assert len(self.classifier.disaster_labels) == 7
        assert "fire" in self.classifier.disaster_labels
    
    @patch('PIL.Image.open')
    def test_predict_image_path(self, mock_image_open):
        # Mock PIL Image
        mock_image = Mock()
        mock_image.convert.return_value = mock_image
        mock_image_open.return_value = mock_image
        
        result = self.classifier.predict("fake_image_path.jpg")
        
        assert "prediction" in result
        assert "confidence" in result
        assert result["prediction"] in self.classifier.disaster_labels
    
    def test_generate_synthetic_image(self):
        image_array = self.classifier.generate_synthetic_image("flood")
        
        assert image_array.shape == (224, 224, 3)
        assert image_array.dtype == np.uint8
        assert np.all(image_array >= 0) and np.all(image_array <= 255)


class TestMultimodalFusionModel:
    
    def setup_method(self):
        self.model = MultimodalFusionModel()
    
    def test_initialization(self):
        assert len(self.model.disaster_labels) == 7
        assert hasattr(self.model, 'text_classifier')
        assert hasattr(self.model, 'image_classifier')
    
    def test_process_weather_data(self):
        weather_data = {
            "wind_speed": 85.0,
            "precipitation": 30.0,
            "temperature": 25.0,
            "pressure": 960.0,
            "humidity": 80.0
        }
        
        features = self.model.process_weather_data(weather_data)
        
        assert len(features) == 6
        assert features[-1] == 1  # extreme_weather_flag should be 1
    
    def test_process_geo_data(self):
        geo_data = {"latitude": 40.7128, "longitude": -74.0060}
        features = self.model.process_geo_data(geo_data)
        
        assert len(features) == 4
        assert all(isinstance(f, float) for f in features)
    
    def test_predict_multimodal(self):
        sample_data = {
            "text": "Flash flood warning issued for downtown area",
            "image_path": None,
            "weather": {
                "wind_speed": 20.0,
                "precipitation": 15.0,
                "temperature": 22.0,
                "pressure": 1013.0,
                "humidity": 65.0
            },
            "geo": {"latitude": 40.7128, "longitude": -74.0060}
        }
        
        result = self.model.predict(sample_data)
        
        assert "prediction" in result
        assert "confidence" in result
        assert "individual_confidences" in result
        assert len(result["individual_confidences"]) == 4


class TestFeatureEngineering:
    
    def test_text_features(self):
        from feature_store.feature_engineering import FeatureEngineer
        fe = FeatureEngineer()
        
        text = "EMERGENCY: Major earthquake detected! Evacuate buildings immediately!"
        features = fe.extract_text_features(text)
        
        assert len(features) == 5
        assert features["text_length"] == len(text)
        assert features["urgency_score"] > 0
        assert features["disaster_keyword_count"] > 0
    
    def test_weather_features(self):
        from feature_store.feature_engineering import FeatureEngineer
        fe = FeatureEngineer()
        
        weather_data = {
            "wind_speed": 95.0,
            "precipitation": 40.0,
            "temperature": 35.0,
            "pressure": 950.0,
            "humidity": 90.0
        }
        
        features = fe.extract_weather_features(weather_data)
        
        assert len(features) == 5
        assert features["pressure_anomaly"] < 0  # Low pressure
        assert features["extreme_weather_score"] > 0