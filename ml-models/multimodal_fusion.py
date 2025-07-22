"""
Multimodal Fusion Model for Disaster Detection
Combines text, image, and sensor data for comprehensive disaster classification
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime
import json

from text_classifier import DisasterTextClassifier
from image_classifier import DisasterImageClassifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultimodalFusionModel(nn.Module):
    """
    Multimodal fusion network that combines:
    - Text embeddings from disaster text classifier
    - Image embeddings from disaster image classifier  
    - Weather sensor features
    - Geospatial features
    """
    
    def __init__(self, text_embedding_dim: int = 768, 
                 image_embedding_dim: int = 2048,
                 weather_feature_dim: int = 6,
                 geo_feature_dim: int = 4,
                 hidden_dim: int = 512,
                 num_classes: int = 7,
                 fusion_method: str = "attention"):
        
        super(MultimodalFusionModel, self).__init__()
        
        self.fusion_method = fusion_method
        self.num_classes = num_classes
        
        # Feature projection layers
        self.text_projection = nn.Linear(text_embedding_dim, hidden_dim)
        self.image_projection = nn.Linear(image_embedding_dim, hidden_dim)
        self.weather_projection = nn.Linear(weather_feature_dim, hidden_dim)
        self.geo_projection = nn.Linear(geo_feature_dim, hidden_dim)
        
        # Fusion layers
        if fusion_method == "attention":
            self.attention_fusion = AttentionFusion(hidden_dim, num_modalities=4)
            fusion_output_dim = hidden_dim
        elif fusion_method == "concat":
            fusion_output_dim = hidden_dim * 4
        else:
            raise ValueError(f"Unsupported fusion method: {fusion_method}")
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(fusion_output_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 2, num_classes)
        )
        
        # Modality-specific confidence estimators
        self.text_confidence = nn.Linear(hidden_dim, 1)
        self.image_confidence = nn.Linear(hidden_dim, 1)
        self.weather_confidence = nn.Linear(hidden_dim, 1)
        self.geo_confidence = nn.Linear(hidden_dim, 1)
    
    def forward(self, text_features: torch.Tensor,
                image_features: torch.Tensor,
                weather_features: torch.Tensor,
                geo_features: torch.Tensor,
                modality_mask: Optional[torch.Tensor] = None):
        """
        Forward pass through multimodal fusion model
        
        Args:
            text_features: Text embeddings [batch_size, text_embedding_dim]
            image_features: Image embeddings [batch_size, image_embedding_dim]
            weather_features: Weather sensor features [batch_size, weather_feature_dim]
            geo_features: Geospatial features [batch_size, geo_feature_dim]
            modality_mask: Binary mask indicating available modalities [batch_size, 4]
        """
        
        # Project features to common dimension
        text_proj = self.text_projection(text_features)
        image_proj = self.image_projection(image_features)
        weather_proj = self.weather_projection(weather_features)
        geo_proj = self.geo_projection(geo_features)
        
        # Apply ReLU activation
        text_proj = F.relu(text_proj)
        image_proj = F.relu(image_proj)
        weather_proj = F.relu(weather_proj)
        geo_proj = F.relu(geo_proj)
        
        # Compute modality-specific confidence scores
        text_conf = torch.sigmoid(self.text_confidence(text_proj))
        image_conf = torch.sigmoid(self.image_confidence(image_proj))
        weather_conf = torch.sigmoid(self.weather_confidence(weather_proj))
        geo_conf = torch.sigmoid(self.geo_confidence(geo_proj))
        
        # Apply modality mask if provided
        if modality_mask is not None:
            text_proj = text_proj * modality_mask[:, 0:1]
            image_proj = image_proj * modality_mask[:, 1:2]
            weather_proj = weather_proj * modality_mask[:, 2:3]
            geo_proj = geo_proj * modality_mask[:, 3:4]
            
            text_conf = text_conf * modality_mask[:, 0:1]
            image_conf = image_conf * modality_mask[:, 1:2]
            weather_conf = weather_conf * modality_mask[:, 2:3]
            geo_conf = geo_conf * modality_mask[:, 3:4]
        
        # Fusion
        if self.fusion_method == "attention":
            # Stack features for attention fusion
            features = torch.stack([text_proj, image_proj, weather_proj, geo_proj], dim=1)
            confidences = torch.stack([text_conf, image_conf, weather_conf, geo_conf], dim=1)
            
            fused_features = self.attention_fusion(features, confidences)
        
        elif self.fusion_method == "concat":
            # Simple concatenation
            fused_features = torch.cat([text_proj, image_proj, weather_proj, geo_proj], dim=1)
        
        # Classification
        logits = self.classifier(fused_features)
        
        return {
            'logits': logits,
            'text_confidence': text_conf,
            'image_confidence': image_conf,
            'weather_confidence': weather_conf,
            'geo_confidence': geo_conf,
            'fused_features': fused_features
        }

class AttentionFusion(nn.Module):
    """Attention-based fusion module for multimodal features"""
    
    def __init__(self, hidden_dim: int, num_modalities: int):
        super(AttentionFusion, self).__init__()
        
        self.hidden_dim = hidden_dim
        self.num_modalities = num_modalities
        
        # Attention mechanism
        self.attention_query = nn.Linear(hidden_dim, hidden_dim)
        self.attention_key = nn.Linear(hidden_dim, hidden_dim)
        self.attention_value = nn.Linear(hidden_dim, hidden_dim)
        
        # Output projection
        self.output_projection = nn.Linear(hidden_dim, hidden_dim)
    
    def forward(self, features: torch.Tensor, confidences: torch.Tensor):
        """
        Apply attention-based fusion
        
        Args:
            features: [batch_size, num_modalities, hidden_dim]
            confidences: [batch_size, num_modalities, 1]
        """
        
        batch_size, num_modalities, hidden_dim = features.shape
        
        # Compute attention weights
        queries = self.attention_query(features)  # [batch_size, num_modalities, hidden_dim]
        keys = self.attention_key(features)
        values = self.attention_value(features)
        
        # Scaled dot-product attention
        attention_scores = torch.bmm(queries, keys.transpose(1, 2)) / (hidden_dim ** 0.5)
        
        # Incorporate confidence scores
        confidence_weights = confidences.expand(-1, -1, num_modalities)
        attention_scores = attention_scores * confidence_weights
        
        # Apply softmax
        attention_weights = F.softmax(attention_scores, dim=-1)
        
        # Apply attention to values
        attended_features = torch.bmm(attention_weights, values)
        
        # Global average pooling across modalities
        fused_features = torch.mean(attended_features, dim=1)
        
        # Output projection
        output = self.output_projection(fused_features)
        
        return output

class DisasterMultimodalClassifier:
    """Complete multimodal disaster classification system"""
    
    def __init__(self, device: str = "auto"):
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        # Initialize individual modality classifiers
        self.text_classifier = None
        self.image_classifier = None
        self.fusion_model = None
        
        # Disaster categories
        self.disaster_labels = {
            0: "no_disaster",
            1: "flood",
            2: "fire",
            3: "earthquake",
            4: "hurricane",
            5: "tornado",
            6: "other_disaster"
        }
        
        logger.info(f"Initialized multimodal classifier on {self.device}")
    
    def initialize_models(self):
        """Initialize all component models"""
        # Text classifier
        self.text_classifier = DisasterTextClassifier()
        self.text_classifier.initialize_model()
        
        # Image classifier
        self.image_classifier = DisasterImageClassifier(model_type="resnet")
        self.image_classifier.initialize_model()
        
        # Fusion model
        self.fusion_model = MultimodalFusionModel(
            text_embedding_dim=768,  # DistilBERT hidden size
            image_embedding_dim=2048,  # ResNet-50 feature size
            weather_feature_dim=6,
            geo_feature_dim=4,
            fusion_method="attention"
        ).to(self.device)
        
        logger.info("All models initialized")
    
    def extract_text_features(self, texts: List[str]) -> torch.Tensor:
        """Extract features from text using the text classifier"""
        # Get hidden states from text classifier
        tokenized = self.text_classifier.tokenizer(
            texts, return_tensors="pt", padding=True, truncation=True, max_length=512
        )
        
        with torch.no_grad():
            outputs = self.text_classifier.model(**tokenized, output_hidden_states=True)
            # Use CLS token representation
            text_features = outputs.hidden_states[-1][:, 0, :]  # [batch_size, 768]
        
        return text_features.to(self.device)
    
    def extract_image_features(self, images: List) -> torch.Tensor:
        """Extract features from images using the image classifier"""
        image_features = []
        
        for image in images:
            with torch.no_grad():
                if self.image_classifier.model_type == "resnet":
                    img_tensor = self.image_classifier.preprocess_image_resnet(image)
                    # Remove the final classification layer to get features
                    features = self.image_classifier.model.avgpool(
                        self.image_classifier.model.layer4(
                            self.image_classifier.model.layer3(
                                self.image_classifier.model.layer2(
                                    self.image_classifier.model.layer1(
                                        self.image_classifier.model.maxpool(
                                            self.image_classifier.model.relu(
                                                self.image_classifier.model.bn1(
                                                    self.image_classifier.model.conv1(img_tensor)
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                    features = features.view(features.size(0), -1)  # Flatten
                else:
                    # ViT features
                    img_tensor = self.image_classifier.preprocess_image_vit(image)
                    outputs = self.image_classifier.model(img_tensor, output_hidden_states=True)
                    features = outputs.hidden_states[-1][:, 0, :]  # CLS token
                
                image_features.append(features)
        
        return torch.cat(image_features, dim=0).to(self.device)
    
    def extract_weather_features(self, weather_data: List[Dict[str, Any]]) -> torch.Tensor:
        """Extract features from weather sensor data"""
        features = []
        
        for data in weather_data:
            feature_vector = [
                data.get('wind_speed_mph', 0.0),
                data.get('precipitation_mm', 0.0),
                data.get('temperature_c', 20.0),
                data.get('pressure_hpa', 1013.0),
                data.get('humidity_percent', 50.0),
                float(data.get('is_extreme', False))
            ]
            features.append(feature_vector)
        
        return torch.tensor(features, dtype=torch.float32).to(self.device)
    
    def extract_geo_features(self, locations: List[Dict[str, float]]) -> torch.Tensor:
        """Extract geospatial features from location data"""
        features = []
        
        for location in locations:
            lat = location.get('lat', 0.0)
            lon = location.get('lon', 0.0)
            
            # Create simple geospatial features
            feature_vector = [
                lat,
                lon,
                np.sin(np.radians(lat)),  # Seasonal component
                np.cos(np.radians(lon))   # Longitude component
            ]
            features.append(feature_vector)
        
        return torch.tensor(features, dtype=torch.float32).to(self.device)
    
    def predict_multimodal(self, 
                          texts: Optional[List[str]] = None,
                          images: Optional[List] = None,
                          weather_data: Optional[List[Dict[str, Any]]] = None,
                          locations: Optional[List[Dict[str, float]]] = None) -> Dict[str, Any]:
        """
        Predict disaster category using multimodal data
        """
        batch_size = max(
            len(texts) if texts else 0,
            len(images) if images else 0,
            len(weather_data) if weather_data else 0,
            len(locations) if locations else 0
        )
        
        if batch_size == 0:
            raise ValueError("At least one modality must be provided")
        
        # Extract features from available modalities
        if texts:
            text_features = self.extract_text_features(texts)
        else:
            text_features = torch.zeros(batch_size, 768).to(self.device)
        
        if images:
            image_features = self.extract_image_features(images)
        else:
            image_features = torch.zeros(batch_size, 2048).to(self.device)
        
        if weather_data:
            weather_features = self.extract_weather_features(weather_data)
        else:
            weather_features = torch.zeros(batch_size, 6).to(self.device)
        
        if locations:
            geo_features = self.extract_geo_features(locations)
        else:
            geo_features = torch.zeros(batch_size, 4).to(self.device)
        
        # Create modality mask
        modality_mask = torch.tensor([
            [1.0 if texts else 0.0,
             1.0 if images else 0.0,
             1.0 if weather_data else 0.0,
             1.0 if locations else 0.0]
        ]).repeat(batch_size, 1).to(self.device)
        
        # Forward pass through fusion model
        self.fusion_model.eval()
        with torch.no_grad():
            outputs = self.fusion_model(
                text_features, image_features, weather_features, geo_features, modality_mask
            )
        
        # Convert to probabilities
        probabilities = F.softmax(outputs['logits'], dim=1)
        
        # Prepare results
        results = []
        for i in range(batch_size):
            result = {
                'predictions': {},
                'confidence_scores': {
                    'text': float(outputs['text_confidence'][i].cpu()),
                    'image': float(outputs['image_confidence'][i].cpu()),
                    'weather': float(outputs['weather_confidence'][i].cpu()),
                    'geo': float(outputs['geo_confidence'][i].cpu())
                },
                'top_prediction': None,
                'top_score': None
            }
            
            # Add probability predictions
            for idx, prob in enumerate(probabilities[i].cpu().numpy()):
                result['predictions'][self.disaster_labels[idx]] = float(prob)
            
            # Find top prediction
            top_idx = torch.argmax(probabilities[i]).item()
            result['top_prediction'] = self.disaster_labels[top_idx]
            result['top_score'] = float(probabilities[i][top_idx].cpu())
            
            results.append(result)
        
        return results if len(results) > 1 else results[0]
    
    def save_fusion_model(self, path: str):
        """Save the trained fusion model"""
        torch.save({
            'model_state_dict': self.fusion_model.state_dict(),
            'disaster_labels': self.disaster_labels,
            'model_config': {
                'text_embedding_dim': 768,
                'image_embedding_dim': 2048,
                'weather_feature_dim': 6,
                'geo_feature_dim': 4,
                'fusion_method': 'attention'
            }
        }, path)
        logger.info(f"Fusion model saved to {path}")
    
    def load_fusion_model(self, path: str):
        """Load a trained fusion model"""
        checkpoint = torch.load(path, map_location=self.device)
        
        self.disaster_labels = checkpoint['disaster_labels']
        config = checkpoint['model_config']
        
        self.fusion_model = MultimodalFusionModel(**config).to(self.device)
        self.fusion_model.load_state_dict(checkpoint['model_state_dict'])
        self.fusion_model.eval()
        
        logger.info(f"Fusion model loaded from {path}")

def main():
    """Test the multimodal fusion system"""
    
    # Initialize classifier
    classifier = DisasterMultimodalClassifier()
    classifier.initialize_models()
    
    # Test data
    test_texts = ["Massive flooding in downtown area, need immediate help!"]
    test_weather = [{'wind_speed_mph': 85.0, 'precipitation_mm': 45.0, 'is_extreme': True}]
    test_locations = [{'lat': 37.7749, 'lon': -122.4194}]
    
    # Test multimodal prediction
    result = classifier.predict_multimodal(
        texts=test_texts,
        weather_data=test_weather,
        locations=test_locations
    )
    
    print("Multimodal Prediction Results:")
    print(f"Top Prediction: {result['top_prediction']} (Score: {result['top_score']:.3f})")
    print(f"All Predictions: {result['predictions']}")
    print(f"Modality Confidences: {result['confidence_scores']}")

if __name__ == "__main__":
    main()