"""
Image Classification Model for Disaster Detection
Uses vision transformer models to classify disaster-related imagery
"""

import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models import resnet50, ResNet50_Weights
from transformers import ViTImageProcessor, ViTForImageClassification
from PIL import Image
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
import json
import base64
import io
from datetime import datetime
import cv2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DisasterImageClassifier:
    """Vision-based classifier for disaster detection in images"""
    
    def __init__(self, model_type: str = "vit", num_classes: int = 7):
        self.model_type = model_type
        self.num_classes = num_classes
        self.model = None
        self.processor = None
        self.transform = None
        
        # Disaster categories for images
        self.disaster_labels = {
            0: "no_disaster",
            1: "flood",
            2: "fire",
            3: "earthquake_damage",
            4: "hurricane_damage",
            5: "tornado_damage",
            6: "other_disaster"
        }
        
        self.label_to_id = {v: k for k, v in self.disaster_labels.items()}
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
    
    def initialize_vit_model(self):
        """Initialize Vision Transformer model"""
        model_name = "google/vit-base-patch16-224-in21k"
        
        self.processor = ViTImageProcessor.from_pretrained(model_name)
        self.model = ViTForImageClassification.from_pretrained(
            model_name,
            num_labels=self.num_classes,
            ignore_mismatched_sizes=True
        )
        
        self.model.to(self.device)
        logger.info("Initialized Vision Transformer model")
    
    def initialize_resnet_model(self):
        """Initialize ResNet-50 model with custom head"""
        self.model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
        
        # Replace classifier head
        num_features = self.model.fc.in_features
        self.model.fc = nn.Linear(num_features, self.num_classes)
        
        self.model.to(self.device)
        
        # Define transforms
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        logger.info("Initialized ResNet-50 model")
    
    def initialize_model(self):
        """Initialize the specified model type"""
        if self.model_type == "vit":
            self.initialize_vit_model()
        elif self.model_type == "resnet":
            self.initialize_resnet_model()
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
    
    def create_synthetic_disaster_image(self, disaster_type: str, size: Tuple[int, int] = (224, 224)) -> Image.Image:
        """Create synthetic disaster images for training"""
        
        # Color schemes for different disasters
        color_schemes = {
            "flood": [(0, 100, 200), (50, 150, 255), (0, 50, 150)],      # Blue tones
            "fire": [(255, 100, 0), (255, 150, 50), (200, 50, 0)],       # Orange/red tones
            "earthquake_damage": [(139, 69, 19), (160, 160, 160), (100, 100, 100)],  # Brown/gray
            "hurricane_damage": [(128, 128, 128), (64, 64, 64), (192, 192, 192)],    # Gray tones
            "tornado_damage": [(101, 67, 33), (139, 69, 19), (160, 82, 45)],         # Brown debris
            "other_disaster": [(165, 42, 42), (255, 255, 0), (255, 165, 0)],         # Mixed colors
            "no_disaster": [(0, 255, 0), (135, 206, 235), (255, 255, 255)]           # Green/blue/white
        }
        
        colors = color_schemes.get(disaster_type, [(128, 128, 128)])
        
        # Create base image with gradient
        img_array = np.zeros((*size, 3), dtype=np.uint8)
        
        for i in range(size[0]):
            for j in range(size[1]):
                # Create patterns based on disaster type
                if disaster_type == "flood":
                    # Water-like patterns
                    wave = int(50 * np.sin(j * 0.1) + 100)
                    img_array[i, j] = [min(wave, 255), min(wave + 50, 255), min(wave + 100, 255)]
                    
                elif disaster_type == "fire":
                    # Fire-like patterns
                    intensity = int(200 + 55 * np.sin(i * 0.1) * np.cos(j * 0.1))
                    img_array[i, j] = [min(intensity, 255), max(intensity - 100, 0), 0]
                    
                elif disaster_type in ["earthquake_damage", "hurricane_damage", "tornado_damage"]:
                    # Debris-like patterns
                    noise = np.random.randint(-30, 30)
                    base_color = colors[np.random.randint(0, len(colors))]
                    img_array[i, j] = [
                        max(0, min(255, base_color[0] + noise)),
                        max(0, min(255, base_color[1] + noise)),
                        max(0, min(255, base_color[2] + noise))
                    ]
                    
                else:
                    # Normal/other patterns
                    base_color = colors[np.random.randint(0, len(colors))]
                    img_array[i, j] = base_color
        
        return Image.fromarray(img_array)
    
    def create_synthetic_dataset(self, num_samples_per_class: int = 500) -> List[Tuple[Image.Image, int]]:
        """Create synthetic training dataset"""
        dataset = []
        
        for label_name, label_id in self.label_to_id.items():
            logger.info(f"Generating {num_samples_per_class} samples for {label_name}")
            
            for _ in range(num_samples_per_class):
                # Create base image
                img = self.create_synthetic_disaster_image(label_name)
                
                # Add random augmentations
                img_array = np.array(img)
                
                # Random brightness
                brightness = np.random.uniform(0.7, 1.3)
                img_array = np.clip(img_array * brightness, 0, 255).astype(np.uint8)
                
                # Random noise
                noise = np.random.normal(0, 10, img_array.shape)
                img_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
                
                # Random blur (sometimes)
                if np.random.random() < 0.3:
                    img_array = cv2.blur(img_array, (3, 3))
                
                final_img = Image.fromarray(img_array)
                dataset.append((final_img, label_id))
        
        # Shuffle dataset
        np.random.shuffle(dataset)
        logger.info(f"Created synthetic dataset with {len(dataset)} images")
        
        return dataset
    
    def preprocess_image_vit(self, image: Image.Image) -> torch.Tensor:
        """Preprocess image for Vision Transformer"""
        inputs = self.processor(images=image, return_tensors="pt")
        return inputs["pixel_values"].to(self.device)
    
    def preprocess_image_resnet(self, image: Image.Image) -> torch.Tensor:
        """Preprocess image for ResNet"""
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        tensor = self.transform(image).unsqueeze(0)
        return tensor.to(self.device)
    
    def train_model(self, dataset: List[Tuple[Image.Image, int]], 
                   epochs: int = 5, batch_size: int = 32):
        """Train the disaster image classification model"""
        
        # Split dataset
        train_size = int(0.8 * len(dataset))
        train_dataset = dataset[:train_size]
        val_dataset = dataset[train_size:]
        
        # Set up training
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-4)
        criterion = nn.CrossEntropyLoss()
        
        best_val_acc = 0.0
        
        for epoch in range(epochs):
            logger.info(f"Epoch {epoch + 1}/{epochs}")
            
            # Training phase
            train_loss = 0.0
            train_correct = 0
            
            for i in range(0, len(train_dataset), batch_size):
                batch = train_dataset[i:i + batch_size]
                
                # Prepare batch
                images = []
                labels = []
                
                for img, label in batch:
                    if self.model_type == "vit":
                        img_tensor = self.preprocess_image_vit(img)
                    else:
                        img_tensor = self.preprocess_image_resnet(img)
                    
                    images.append(img_tensor)
                    labels.append(label)
                
                # Stack images and labels
                if self.model_type == "vit":
                    batch_images = torch.cat(images, dim=0)
                else:
                    batch_images = torch.cat(images, dim=0)
                
                batch_labels = torch.tensor(labels).to(self.device)
                
                # Forward pass
                optimizer.zero_grad()
                
                if self.model_type == "vit":
                    outputs = self.model(batch_images)
                    logits = outputs.logits
                else:
                    logits = self.model(batch_images)
                
                loss = criterion(logits, batch_labels)
                
                # Backward pass
                loss.backward()
                optimizer.step()
                
                # Statistics
                train_loss += loss.item()
                _, predicted = torch.max(logits.data, 1)
                train_correct += (predicted == batch_labels).sum().item()
            
            train_acc = train_correct / len(train_dataset)
            avg_train_loss = train_loss / (len(train_dataset) // batch_size)
            
            # Validation phase
            val_acc = self.evaluate_model(val_dataset, batch_size)
            
            logger.info(f"Train Loss: {avg_train_loss:.4f}, "
                       f"Train Acc: {train_acc:.4f}, "
                       f"Val Acc: {val_acc:.4f}")
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                torch.save(self.model.state_dict(), f"best_disaster_image_model_{self.model_type}.pth")
        
        logger.info(f"Training completed. Best validation accuracy: {best_val_acc:.4f}")
    
    def evaluate_model(self, dataset: List[Tuple[Image.Image, int]], 
                      batch_size: int = 32) -> float:
        """Evaluate model on dataset"""
        self.model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for i in range(0, len(dataset), batch_size):
                batch = dataset[i:i + batch_size]
                
                images = []
                labels = []
                
                for img, label in batch:
                    if self.model_type == "vit":
                        img_tensor = self.preprocess_image_vit(img)
                    else:
                        img_tensor = self.preprocess_image_resnet(img)
                    
                    images.append(img_tensor)
                    labels.append(label)
                
                if self.model_type == "vit":
                    batch_images = torch.cat(images, dim=0)
                else:
                    batch_images = torch.cat(images, dim=0)
                
                batch_labels = torch.tensor(labels).to(self.device)
                
                if self.model_type == "vit":
                    outputs = self.model(batch_images)
                    logits = outputs.logits
                else:
                    logits = self.model(batch_images)
                
                _, predicted = torch.max(logits.data, 1)
                total += batch_labels.size(0)
                correct += (predicted == batch_labels).sum().item()
        
        return correct / total
    
    def predict(self, image: Image.Image) -> Dict[str, float]:
        """Predict disaster category for single image"""
        self.model.eval()
        
        with torch.no_grad():
            if self.model_type == "vit":
                img_tensor = self.preprocess_image_vit(image)
                outputs = self.model(img_tensor)
                logits = outputs.logits
            else:
                img_tensor = self.preprocess_image_resnet(image)
                logits = self.model(img_tensor)
            
            probabilities = torch.nn.functional.softmax(logits, dim=1)[0]
            
            result = {}
            for idx, prob in enumerate(probabilities.cpu().numpy()):
                result[self.disaster_labels[idx]] = float(prob)
            
            return result
    
    def predict_from_base64(self, base64_str: str) -> Dict[str, float]:
        """Predict from base64 encoded image"""
        # Decode base64 to image
        image_bytes = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_bytes))
        
        return self.predict(image)
    
    def get_top_prediction(self, image: Image.Image) -> Tuple[str, float]:
        """Get top prediction for image"""
        results = self.predict(image)
        top_label = max(results.keys(), key=lambda k: results[k])
        top_score = results[top_label]
        return top_label, top_score
    
    def save_model(self, path: str):
        """Save trained model"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'model_type': self.model_type,
            'num_classes': self.num_classes,
            'disaster_labels': self.disaster_labels,
            'label_to_id': self.label_to_id,
        }, path)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load trained model"""
        checkpoint = torch.load(path, map_location=self.device)
        
        self.model_type = checkpoint['model_type']
        self.num_classes = checkpoint['num_classes']
        self.disaster_labels = checkpoint['disaster_labels']
        self.label_to_id = checkpoint['label_to_id']
        
        # Initialize model architecture
        self.initialize_model()
        
        # Load weights
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        logger.info(f"Model loaded from {path}")

def main():
    """Train and test the disaster image classifier"""
    
    # Initialize classifier
    classifier = DisasterImageClassifier(model_type="resnet")  # Use ResNet for faster training
    classifier.initialize_model()
    
    # Create synthetic dataset
    dataset = classifier.create_synthetic_dataset(num_samples_per_class=200)  # Smaller for demo
    
    # Train model
    classifier.train_model(dataset, epochs=3, batch_size=16)
    
    # Save model
    classifier.save_model("disaster_image_model.pth")
    
    # Test predictions
    test_disasters = ["flood", "fire", "no_disaster"]
    
    print("\nTest Predictions:")
    for disaster_type in test_disasters:
        test_img = classifier.create_synthetic_disaster_image(disaster_type)
        prediction = classifier.predict(test_img)
        top_label, top_score = classifier.get_top_prediction(test_img)
        
        print(f"Disaster Type: {disaster_type}")
        print(f"Top Prediction: {top_label} (confidence: {top_score:.3f})")
        print(f"All Predictions: {prediction}")
        print("-" * 50)

if __name__ == "__main__":
    main()