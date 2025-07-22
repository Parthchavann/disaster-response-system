"""
Text Classification Model for Disaster Detection
Uses transformer models to classify social media text for disaster events
"""

import torch
import torch.nn as nn
from transformers import (
    AutoTokenizer, AutoModel, AutoModelForSequenceClassification,
    TrainingArguments, Trainer, DataCollatorWithPadding
)
from datasets import Dataset, DatasetDict
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from typing import Dict, List, Tuple, Optional
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DisasterTextClassifier:
    """Transformer-based text classifier for disaster detection"""
    
    def __init__(self, model_name: str = "distilbert-base-uncased", num_labels: int = 7):
        self.model_name = model_name
        self.num_labels = num_labels
        self.tokenizer = None
        self.model = None
        self.trainer = None
        
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
        
        self.label_to_id = {v: k for k, v in self.disaster_labels.items()}
        
    def initialize_model(self):
        """Initialize tokenizer and model"""
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=self.num_labels,
            problem_type="single_label_classification"
        )
        logger.info(f"Initialized model: {self.model_name}")
    
    def create_synthetic_dataset(self, num_samples: int = 5000) -> DatasetDict:
        """Create synthetic training dataset for disaster classification"""
        
        # Disaster-related text patterns
        disaster_texts = {
            "flood": [
                "The river is overflowing and flooding the streets",
                "Water levels rising rapidly in downtown area",
                "Flash flood warning issued for our county",
                "Houses underwater after dam broke",
                "Severe flooding blocking all roads",
                "Storm surge causing coastal flooding",
                "Heavy rain leads to urban flooding"
            ],
            "fire": [
                "Wildfire spreading rapidly through forest",
                "Building on fire, smoke visible for miles",
                "Evacuation ordered due to approaching fires",
                "Forest fire threatening residential areas",
                "Smoke and flames visible from highway",
                "Fire department battling massive blaze",
                "Brush fire growing out of control"
            ],
            "earthquake": [
                "Strong earthquake felt across the region",
                "Ground shaking, buildings swaying",
                "Earthquake damage to infrastructure",
                "Aftershocks continuing after main quake",
                "Seismic activity detected in area",
                "Tremors felt, people evacuating buildings",
                "Earthquake registered 6.2 on Richter scale"
            ],
            "hurricane": [
                "Hurricane making landfall with 120mph winds",
                "Category 4 storm approaching coast",
                "Hurricane warnings in effect for region",
                "Strong winds and heavy rain from storm",
                "Tropical storm developing into hurricane",
                "Storm surge and flooding from hurricane",
                "Hurricane evacuation zones activated"
            ],
            "tornado": [
                "Tornado spotted moving through town",
                "Funnel cloud touchdown confirmed",
                "Tornado warning issued for county",
                "Severe weather producing tornadoes",
                "Twister damage path visible from air",
                "Multiple tornadoes reported in area",
                "Tornado sirens activated across city"
            ],
            "other_disaster": [
                "Landslide blocking mountain highway",
                "Sinkhole opens up in city street",
                "Volcanic ash affecting air travel",
                "Severe thunderstorm with large hail",
                "Blizzard conditions with zero visibility",
                "Mudslide threatens homes on hillside",
                "Ice storm causing power outages"
            ],
            "no_disaster": [
                "Beautiful sunny day at the beach",
                "Having lunch at my favorite restaurant",
                "Traffic is moving smoothly today",
                "Enjoying the concert in the park",
                "Weekend plans include hiking",
                "Meeting friends for coffee later",
                "Great weather for outdoor activities"
            ]
        }
        
        # Generate synthetic samples
        texts = []
        labels = []
        
        samples_per_class = num_samples // len(disaster_texts)
        
        for label, text_templates in disaster_texts.items():
            for _ in range(samples_per_class):
                # Add variations to templates
                base_text = np.random.choice(text_templates)
                
                # Add contextual variations
                variations = [
                    f"URGENT: {base_text}",
                    f"Breaking news: {base_text}",
                    f"Emergency alert: {base_text}",
                    f"Just witnessed: {base_text}",
                    base_text,
                    f"{base_text} #emergency",
                    f"{base_text} Need help!",
                ]
                
                text = np.random.choice(variations)
                texts.append(text)
                labels.append(self.label_to_id[label])
        
        # Create DataFrame and split
        df = pd.DataFrame({'text': texts, 'label': labels})
        df = df.sample(frac=1).reset_index(drop=True)  # Shuffle
        
        # Split into train/validation/test
        train_size = int(0.7 * len(df))
        val_size = int(0.2 * len(df))
        
        train_df = df[:train_size]
        val_df = df[train_size:train_size + val_size]
        test_df = df[train_size + val_size:]
        
        # Convert to Hugging Face datasets
        train_dataset = Dataset.from_pandas(train_df)
        val_dataset = Dataset.from_pandas(val_df)
        test_dataset = Dataset.from_pandas(test_df)
        
        dataset_dict = DatasetDict({
            'train': train_dataset,
            'validation': val_dataset,
            'test': test_dataset
        })
        
        logger.info(f"Created synthetic dataset with {len(df)} samples")
        return dataset_dict
    
    def preprocess_function(self, examples):
        """Tokenize text data"""
        return self.tokenizer(
            examples['text'],
            truncation=True,
            padding=True,
            max_length=512
        )
    
    def compute_metrics(self, eval_pred):
        """Compute evaluation metrics"""
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, predictions, average='weighted'
        )
        accuracy = accuracy_score(labels, predictions)
        
        return {
            'accuracy': accuracy,
            'f1': f1,
            'precision': precision,
            'recall': recall
        }
    
    def train_model(self, dataset: DatasetDict, output_dir: str = "./disaster_text_model"):
        """Train the disaster classification model"""
        
        # Tokenize datasets
        tokenized_dataset = dataset.map(
            self.preprocess_function,
            batched=True,
            remove_columns=dataset['train'].column_names
        )
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            learning_rate=2e-5,
            per_device_train_batch_size=16,
            per_device_eval_batch_size=16,
            num_train_epochs=3,
            weight_decay=0.01,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            push_to_hub=False,
            logging_dir=f"{output_dir}/logs",
            logging_steps=100,
            save_total_limit=2,
            metric_for_best_model="f1",
            greater_is_better=True,
        )
        
        # Data collator
        data_collator = DataCollatorWithPadding(tokenizer=self.tokenizer)
        
        # Initialize trainer
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=tokenized_dataset['train'],
            eval_dataset=tokenized_dataset['validation'],
            tokenizer=self.tokenizer,
            data_collator=data_collator,
            compute_metrics=self.compute_metrics,
        )
        
        logger.info("Starting model training...")
        self.trainer.train()
        
        # Evaluate on test set
        test_results = self.trainer.evaluate(tokenized_dataset['test'])
        logger.info(f"Test results: {test_results}")
        
        # Save model
        self.trainer.save_model()
        logger.info(f"Model saved to {output_dir}")
        
        return test_results
    
    def predict(self, texts: List[str]) -> List[Dict[str, float]]:
        """Predict disaster categories for input texts"""
        if not self.model or not self.tokenizer:
            raise ValueError("Model not initialized. Call initialize_model() first.")
        
        # Tokenize inputs
        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512
        )
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        # Convert to readable format
        results = []
        for pred in predictions:
            result = {}
            for idx, score in enumerate(pred.tolist()):
                result[self.disaster_labels[idx]] = score
            results.append(result)
        
        return results
    
    def predict_batch(self, texts: List[str], batch_size: int = 32) -> List[Dict[str, float]]:
        """Predict in batches for large inputs"""
        all_results = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_results = self.predict(batch_texts)
            all_results.extend(batch_results)
        
        return all_results
    
    def get_top_prediction(self, text: str) -> Tuple[str, float]:
        """Get the top prediction for a single text"""
        results = self.predict([text])[0]
        top_label = max(results.keys(), key=lambda k: results[k])
        top_score = results[top_label]
        return top_label, top_score
    
    def save_model_info(self, output_dir: str):
        """Save model metadata and configuration"""
        model_info = {
            'model_name': self.model_name,
            'num_labels': self.num_labels,
            'disaster_labels': self.disaster_labels,
            'label_to_id': self.label_to_id,
            'created_at': datetime.now().isoformat(),
            'model_type': 'disaster_text_classifier'
        }
        
        with open(f"{output_dir}/model_info.json", 'w') as f:
            json.dump(model_info, f, indent=2)
        
        logger.info(f"Model info saved to {output_dir}/model_info.json")

def main():
    """Train and test the disaster text classifier"""
    
    # Initialize classifier
    classifier = DisasterTextClassifier()
    classifier.initialize_model()
    
    # Create synthetic dataset
    dataset = classifier.create_synthetic_dataset(num_samples=7000)
    
    # Train model
    results = classifier.train_model(dataset)
    
    # Save model info
    classifier.save_model_info("./disaster_text_model")
    
    # Test predictions
    test_texts = [
        "Massive flooding in downtown area, people trapped!",
        "Beautiful sunset over the lake today",
        "Wildfire spreading rapidly, evacuation needed",
        "Earthquake felt strongly, buildings shaking"
    ]
    
    predictions = classifier.predict(test_texts)
    
    print("\nTest Predictions:")
    for text, pred in zip(test_texts, predictions):
        top_label = max(pred.keys(), key=lambda k: pred[k])
        top_score = pred[top_label]
        print(f"Text: {text}")
        print(f"Prediction: {top_label} (confidence: {top_score:.3f})")
        print("-" * 50)

if __name__ == "__main__":
    main()