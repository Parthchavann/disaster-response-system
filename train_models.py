#!/usr/bin/env python3
"""
Train and save all ML models for the disaster response system.
This script trains the text classifier, image classifier, and multimodal fusion model.
"""

import os
import sys
import logging
import torch
import pickle
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(__file__))

from ml_models.text_classifier import DisasterTextClassifier
from ml_models.image_classifier import DisasterImageClassifier
from ml_models.multimodal_fusion import MultimodalFusionModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create models directory if it doesn't exist
MODELS_DIR = Path("trained_models")
MODELS_DIR.mkdir(exist_ok=True)


def train_text_classifier():
    """Train and save the text classifier model."""
    logger.info("Training text classifier...")
    
    text_classifier = DisasterTextClassifier()
    
    # Train the model (this will use synthetic training data)
    text_classifier.train()
    
    # Save the trained model
    model_path = MODELS_DIR / "text_classifier.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(text_classifier, f)
    
    logger.info(f"Text classifier saved to {model_path}")
    
    # Save model components separately for production use
    torch.save(text_classifier.model.state_dict(), MODELS_DIR / "text_model_state.pth")
    torch.save(text_classifier.tokenizer, MODELS_DIR / "text_tokenizer.pkl")
    
    return text_classifier


def train_image_classifier():
    """Train and save the image classifier model."""
    logger.info("Training image classifier...")
    
    image_classifier = DisasterImageClassifier()
    
    # Train the model (this will use synthetic training data)
    image_classifier.train()
    
    # Save the trained model
    model_path = MODELS_DIR / "image_classifier.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(image_classifier, f)
    
    logger.info(f"Image classifier saved to {model_path}")
    
    # Save model state for production use
    torch.save(image_classifier.model.state_dict(), MODELS_DIR / "image_model_state.pth")
    
    return image_classifier


def train_multimodal_model(text_classifier, image_classifier):
    """Train and save the multimodal fusion model."""
    logger.info("Training multimodal fusion model...")
    
    # Initialize with pre-trained classifiers
    multimodal_model = MultimodalFusionModel()
    multimodal_model.text_classifier = text_classifier
    multimodal_model.image_classifier = image_classifier
    
    # Train the fusion model
    multimodal_model.train()
    
    # Save the complete model
    model_path = MODELS_DIR / "multimodal_fusion.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(multimodal_model, f)
    
    logger.info(f"Multimodal fusion model saved to {model_path}")
    
    # Save fusion model state
    torch.save(multimodal_model.fusion_model.state_dict(), MODELS_DIR / "fusion_model_state.pth")
    
    return multimodal_model


def evaluate_models(text_classifier, image_classifier, multimodal_model):
    """Evaluate all trained models and save performance metrics."""
    logger.info("Evaluating trained models...")
    
    evaluation_results = {
        "text_classifier": {},
        "image_classifier": {},
        "multimodal_model": {}
    }
    
    # Test text classifier
    test_texts = [
        "Flash flood warning issued for downtown area",
        "Wildfire spreading rapidly near residential zone",
        "Earthquake magnitude 6.2 detected this morning",
        "Beautiful sunny day at the beach",
        "Hurricane Category 3 approaching coastline"
    ]
    
    text_predictions = []
    for text in test_texts:
        result = text_classifier.predict(text)
        text_predictions.append(result)
        logger.info(f"Text: '{text[:50]}...' -> {result['prediction']} ({result['confidence']:.3f})")
    
    evaluation_results["text_classifier"]["test_predictions"] = text_predictions
    
    # Test image classifier with synthetic images
    disaster_types = ["flood", "fire", "earthquake", "hurricane", "tornado"]
    image_predictions = []
    
    for disaster_type in disaster_types:
        # Generate synthetic image and test
        synthetic_image = image_classifier.generate_synthetic_image(disaster_type)
        result = image_classifier.predict_array(synthetic_image)
        image_predictions.append(result)
        logger.info(f"Synthetic {disaster_type} image -> {result['prediction']} ({result['confidence']:.3f})")
    
    evaluation_results["image_classifier"]["test_predictions"] = image_predictions
    
    # Test multimodal model
    multimodal_test_cases = [
        {
            "text": "Major flood emergency downtown",
            "weather": {"wind_speed": 25, "precipitation": 45, "temperature": 20, "pressure": 995, "humidity": 90},
            "geo": {"latitude": 40.7128, "longitude": -74.0060}
        },
        {
            "text": "Wildfire alert residential area",
            "weather": {"wind_speed": 60, "precipitation": 0, "temperature": 38, "pressure": 1015, "humidity": 20},
            "geo": {"latitude": 34.0522, "longitude": -118.2437}
        }
    ]
    
    multimodal_predictions = []
    for i, test_case in enumerate(multimodal_test_cases):
        result = multimodal_model.predict(test_case)
        multimodal_predictions.append(result)
        logger.info(f"Multimodal test {i+1} -> {result['prediction']} ({result['confidence']:.3f})")
    
    evaluation_results["multimodal_model"]["test_predictions"] = multimodal_predictions
    
    # Save evaluation results
    eval_path = MODELS_DIR / "evaluation_results.pkl"
    with open(eval_path, 'wb') as f:
        pickle.dump(evaluation_results, f)
    
    logger.info(f"Evaluation results saved to {eval_path}")
    
    return evaluation_results


def main():
    """Main training pipeline."""
    logger.info("Starting model training pipeline...")
    
    try:
        # Train individual models
        text_classifier = train_text_classifier()
        image_classifier = train_image_classifier()
        
        # Train multimodal fusion model
        multimodal_model = train_multimodal_model(text_classifier, image_classifier)
        
        # Evaluate all models
        evaluation_results = evaluate_models(text_classifier, image_classifier, multimodal_model)
        
        # Create a model registry file
        registry = {
            "text_classifier": {
                "path": "trained_models/text_classifier.pkl",
                "state_dict": "trained_models/text_model_state.pth",
                "tokenizer": "trained_models/text_tokenizer.pkl",
                "trained_date": str(torch.datetime.datetime.now()),
                "disaster_labels": text_classifier.disaster_labels
            },
            "image_classifier": {
                "path": "trained_models/image_classifier.pkl", 
                "state_dict": "trained_models/image_model_state.pth",
                "trained_date": str(torch.datetime.datetime.now()),
                "disaster_labels": image_classifier.disaster_labels
            },
            "multimodal_fusion": {
                "path": "trained_models/multimodal_fusion.pkl",
                "state_dict": "trained_models/fusion_model_state.pth",
                "trained_date": str(torch.datetime.datetime.now()),
                "disaster_labels": multimodal_model.disaster_labels
            }
        }
        
        registry_path = MODELS_DIR / "model_registry.pkl"
        with open(registry_path, 'wb') as f:
            pickle.dump(registry, f)
        
        logger.info(f"Model registry saved to {registry_path}")
        logger.info("✅ All models trained and saved successfully!")
        
        # Print summary
        print("\n" + "="*50)
        print("MODEL TRAINING SUMMARY")
        print("="*50)
        print(f"📁 Models saved in: {MODELS_DIR.absolute()}")
        print(f"📊 Text classifier: {len(text_classifier.disaster_labels)} categories")
        print(f"🖼️  Image classifier: {len(image_classifier.disaster_labels)} categories") 
        print(f"🔗 Multimodal fusion: 4 input modalities")
        print(f"✅ All models ready for production use")
        
    except Exception as e:
        logger.error(f"Training failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()