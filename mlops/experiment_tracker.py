"""
MLOps Pipeline for Disaster Response System
Experiment tracking, model versioning, and automated retraining
"""

import mlflow
import mlflow.pytorch
import mlflow.sklearn
from mlflow.tracking import MlflowClient
import wandb
import numpy as np
import pandas as pd
import torch
import pickle
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import os
import shutil
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Import our models
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ml_models.text_classifier import DisasterTextClassifier
from ml_models.image_classifier import DisasterImageClassifier
from ml_models.multimodal_fusion import DisasterMultimodalClassifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DisasterMLOpsManager:
    """MLOps manager for disaster response models"""
    
    def __init__(self, tracking_uri: str = "sqlite:///mlruns.db", 
                 experiment_name: str = "disaster_response"):
        
        # Initialize MLflow
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient()
        
        # Create or get experiment
        try:
            self.experiment = mlflow.create_experiment(experiment_name)
        except mlflow.exceptions.MlflowException:
            self.experiment = mlflow.get_experiment_by_name(experiment_name)
            if self.experiment:
                self.experiment = self.experiment.experiment_id
        
        # Initialize Weights & Biases
        self.wandb_project = "disaster-response-system"
        
        # Model registry
        self.model_registry = {
            'text_classifier': 'disaster_text_classifier',
            'image_classifier': 'disaster_image_classifier',
            'multimodal_fusion': 'disaster_multimodal_fusion'
        }
        
        # Performance thresholds
        self.performance_thresholds = {
            'accuracy': 0.85,
            'f1_score': 0.80,
            'precision': 0.80,
            'recall': 0.80
        }
        
        logger.info("MLOps manager initialized")
    
    def start_experiment(self, run_name: str, model_type: str, 
                        config: Dict[str, Any]) -> str:
        """Start a new experiment run"""
        
        # Start MLflow run
        mlflow.set_experiment(experiment_id=self.experiment)
        run = mlflow.start_run(run_name=run_name)
        
        # Log parameters
        mlflow.log_params(config)
        mlflow.log_param("model_type", model_type)
        mlflow.log_param("start_time", datetime.now().isoformat())
        
        # Start W&B run
        wandb.init(
            project=self.wandb_project,
            name=run_name,
            config=config,
            tags=[model_type, "disaster_response"]
        )
        
        logger.info(f"Started experiment: {run_name}")
        return run.info.run_id
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """Log metrics to both MLflow and W&B"""
        
        # Log to MLflow
        for key, value in metrics.items():
            mlflow.log_metric(key, value, step=step)
        
        # Log to W&B
        wandb.log(metrics, step=step)
        
        logger.info(f"Logged metrics: {metrics}")
    
    def log_artifacts(self, artifacts: Dict[str, str]):
        """Log artifacts (plots, models, data)"""
        
        for name, path in artifacts.items():
            if os.path.exists(path):
                # Log to MLflow
                mlflow.log_artifact(path, artifact_path=name)
                
                # Log to W&B
                wandb.save(path)
                
                logger.info(f"Logged artifact: {name} -> {path}")
    
    def log_model_performance(self, model_type: str, y_true: np.ndarray, 
                            y_pred: np.ndarray, class_names: List[str]):
        """Log comprehensive model performance metrics"""
        
        # Calculate metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='weighted'
        )
        
        # Per-class metrics
        precision_per_class, recall_per_class, f1_per_class, _ = precision_recall_fscore_support(
            y_true, y_pred, average=None, labels=range(len(class_names))
        )
        
        # Log overall metrics
        overall_metrics = {
            'accuracy': accuracy,
            'precision_weighted': precision,
            'recall_weighted': recall,
            'f1_weighted': f1
        }
        self.log_metrics(overall_metrics)
        
        # Log per-class metrics
        for i, class_name in enumerate(class_names):
            if i < len(precision_per_class):
                class_metrics = {
                    f'precision_{class_name}': precision_per_class[i],
                    f'recall_{class_name}': recall_per_class[i],
                    f'f1_{class_name}': f1_per_class[i]
                }
                self.log_metrics(class_metrics)
        
        # Generate and log confusion matrix
        cm_path = self.create_confusion_matrix(y_true, y_pred, class_names, model_type)
        if cm_path:
            self.log_artifacts({'confusion_matrix': cm_path})
        
        # Generate classification report
        report = self.create_classification_report(y_true, y_pred, class_names)
        report_path = f"classification_report_{model_type}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        self.log_artifacts({'classification_report': report_path})
        
        return overall_metrics
    
    def create_confusion_matrix(self, y_true: np.ndarray, y_pred: np.ndarray, 
                              class_names: List[str], model_type: str) -> str:
        """Create and save confusion matrix plot"""
        
        try:
            cm = confusion_matrix(y_true, y_pred)
            
            plt.figure(figsize=(10, 8))
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                       xticklabels=class_names, yticklabels=class_names)
            plt.title(f'Confusion Matrix - {model_type}')
            plt.ylabel('True Label')
            plt.xlabel('Predicted Label')
            
            plot_path = f"confusion_matrix_{model_type}.png"
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return plot_path
            
        except Exception as e:
            logger.error(f"Error creating confusion matrix: {e}")
            return None
    
    def create_classification_report(self, y_true: np.ndarray, y_pred: np.ndarray, 
                                   class_names: List[str]) -> Dict[str, Any]:
        """Create detailed classification report"""
        
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true, y_pred, average=None, labels=range(len(class_names))
        )
        
        report = {
            'overall': {
                'accuracy': float(accuracy),
                'samples': len(y_true)
            },
            'per_class': {}
        }
        
        for i, class_name in enumerate(class_names):
            if i < len(precision):
                report['per_class'][class_name] = {
                    'precision': float(precision[i]),
                    'recall': float(recall[i]),
                    'f1_score': float(f1[i]),
                    'support': int(support[i])
                }
        
        return report
    
    def register_model(self, model_path: str, model_type: str, 
                      metrics: Dict[str, float], 
                      model_version: Optional[str] = None) -> str:
        """Register model in MLflow model registry"""
        
        model_name = self.model_registry[model_type]
        
        # Log model to MLflow
        if model_type == 'text_classifier':
            mlflow.pytorch.log_model(
                pytorch_model=model_path,
                artifact_path="model",
                registered_model_name=model_name
            )
        elif model_type == 'image_classifier':
            mlflow.pytorch.log_model(
                pytorch_model=model_path,
                artifact_path="model", 
                registered_model_name=model_name
            )
        elif model_type == 'multimodal_fusion':
            mlflow.pytorch.log_model(
                pytorch_model=model_path,
                artifact_path="model",
                registered_model_name=model_name
            )
        
        # Get the latest version
        latest_version = self.client.get_latest_versions(
            model_name, stages=["None"]
        )[0]
        
        # Add model description
        self.client.update_model_version(
            name=model_name,
            version=latest_version.version,
            description=f"Model trained on {datetime.now().strftime('%Y-%m-%d')} "
                       f"with accuracy: {metrics.get('accuracy', 0):.3f}"
        )
        
        logger.info(f"Registered model {model_name} version {latest_version.version}")
        return latest_version.version
    
    def promote_model(self, model_type: str, version: str, 
                     stage: str = "Production") -> bool:
        """Promote model to production stage"""
        
        model_name = self.model_registry[model_type]
        
        try:
            # Archive current production model
            current_prod_versions = self.client.get_latest_versions(
                model_name, stages=["Production"]
            )
            
            for version_info in current_prod_versions:
                self.client.transition_model_version_stage(
                    name=model_name,
                    version=version_info.version,
                    stage="Archived"
                )
            
            # Promote new model
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage
            )
            
            logger.info(f"Promoted {model_name} v{version} to {stage}")
            return True
            
        except Exception as e:
            logger.error(f"Error promoting model: {e}")
            return False
    
    def get_production_model(self, model_type: str) -> Optional[str]:
        """Get current production model version"""
        
        model_name = self.model_registry[model_type]
        
        try:
            production_versions = self.client.get_latest_versions(
                model_name, stages=["Production"]
            )
            
            if production_versions:
                return production_versions[0].version
            return None
            
        except Exception as e:
            logger.error(f"Error getting production model: {e}")
            return None
    
    def should_retrain(self, model_type: str, recent_metrics: Dict[str, float]) -> bool:
        """Determine if model should be retrained based on performance drift"""
        
        # Check if metrics fall below thresholds
        for metric, threshold in self.performance_thresholds.items():
            if metric in recent_metrics and recent_metrics[metric] < threshold:
                logger.warning(f"Model {model_type} {metric} below threshold: "
                             f"{recent_metrics[metric]:.3f} < {threshold}")
                return True
        
        # Check historical performance
        try:
            runs = mlflow.search_runs(
                experiment_ids=[self.experiment],
                filter_string=f"params.model_type = '{model_type}'",
                order_by=["start_time DESC"],
                max_results=10
            )
            
            if len(runs) > 5:
                # Check if recent performance is significantly worse
                recent_accuracy = runs.head(3)['metrics.accuracy'].mean()
                historical_accuracy = runs.tail(3)['metrics.accuracy'].mean()
                
                if recent_accuracy < historical_accuracy * 0.95:  # 5% drop
                    logger.warning(f"Performance drift detected for {model_type}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error checking historical performance: {e}")
        
        return False
    
    def automated_retraining_pipeline(self, model_type: str, 
                                    training_data: Dict[str, Any],
                                    validation_data: Dict[str, Any]) -> bool:
        """Automated retraining pipeline"""
        
        logger.info(f"Starting automated retraining for {model_type}")
        
        # Start experiment
        run_name = f"auto_retrain_{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        config = {
            'auto_retrain': True,
            'model_type': model_type,
            'training_samples': len(training_data.get('X', [])),
            'validation_samples': len(validation_data.get('X', []))
        }
        
        run_id = self.start_experiment(run_name, model_type, config)
        
        try:
            # Train model based on type
            if model_type == 'text_classifier':
                model, metrics = self.retrain_text_classifier(training_data, validation_data)
            elif model_type == 'image_classifier':
                model, metrics = self.retrain_image_classifier(training_data, validation_data)
            elif model_type == 'multimodal_fusion':
                model, metrics = self.retrain_multimodal_fusion(training_data, validation_data)
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
            
            # Log performance
            self.log_model_performance(
                model_type, 
                validation_data['y'], 
                model.predict(validation_data['X']),
                validation_data.get('class_names', [])
            )
            
            # Check if model meets quality thresholds
            if self.meets_quality_thresholds(metrics):
                # Save and register model
                model_path = f"retrained_{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
                pickle.dump(model, open(model_path, 'wb'))
                
                version = self.register_model(model_path, model_type, metrics)
                
                # Auto-promote if significantly better
                if self.should_auto_promote(model_type, metrics):
                    self.promote_model(model_type, version, "Production")
                
                logger.info(f"Automated retraining successful for {model_type}")
                return True
            
            else:
                logger.warning(f"Retrained model for {model_type} does not meet quality thresholds")
                return False
                
        except Exception as e:
            logger.error(f"Automated retraining failed for {model_type}: {e}")
            return False
        
        finally:
            mlflow.end_run()
            wandb.finish()
    
    def retrain_text_classifier(self, training_data: Dict, validation_data: Dict) -> Tuple[Any, Dict]:
        """Retrain text classifier"""
        
        classifier = DisasterTextClassifier()
        classifier.initialize_model()
        
        # Convert data to required format
        # This would need to be adapted based on actual data format
        train_dataset = self.prepare_text_dataset(training_data)
        
        # Train model
        results = classifier.train_model(train_dataset)
        
        # Calculate metrics on validation set
        val_predictions = classifier.predict_batch(validation_data['texts'])
        y_pred = [max(pred.keys(), key=lambda k: pred[k]) for pred in val_predictions]
        
        metrics = {
            'accuracy': accuracy_score(validation_data['y'], y_pred),
            'test_accuracy': results.get('eval_accuracy', 0)
        }
        
        return classifier, metrics
    
    def retrain_image_classifier(self, training_data: Dict, validation_data: Dict) -> Tuple[Any, Dict]:
        """Retrain image classifier"""
        
        classifier = DisasterImageClassifier()
        classifier.initialize_model()
        
        # Prepare training data
        train_dataset = self.prepare_image_dataset(training_data)
        
        # Train model
        classifier.train_model(train_dataset, epochs=3)
        
        # Evaluate
        val_accuracy = classifier.evaluate_model(validation_data['images_and_labels'])
        
        metrics = {
            'accuracy': val_accuracy,
            'validation_accuracy': val_accuracy
        }
        
        return classifier, metrics
    
    def retrain_multimodal_fusion(self, training_data: Dict, validation_data: Dict) -> Tuple[Any, Dict]:
        """Retrain multimodal fusion model"""
        
        classifier = DisasterMultimodalClassifier()
        classifier.initialize_models()
        
        # This would require more complex training pipeline
        # For now, return placeholder
        metrics = {'accuracy': 0.85}
        
        return classifier, metrics
    
    def prepare_text_dataset(self, data: Dict) -> Any:
        """Prepare text dataset for training"""
        # Convert to required format for text classifier
        # This is a placeholder - actual implementation would depend on data format
        return data
    
    def prepare_image_dataset(self, data: Dict) -> Any:
        """Prepare image dataset for training"""
        # Convert to required format for image classifier
        return data
    
    def meets_quality_thresholds(self, metrics: Dict[str, float]) -> bool:
        """Check if model meets quality thresholds"""
        
        for metric, threshold in self.performance_thresholds.items():
            if metric in metrics and metrics[metric] < threshold:
                return False
        
        return True
    
    def should_auto_promote(self, model_type: str, metrics: Dict[str, float]) -> bool:
        """Determine if model should be auto-promoted to production"""
        
        # Get current production model performance
        try:
            prod_version = self.get_production_model(model_type)
            if not prod_version:
                return True  # No production model, promote this one
            
            # Compare with current production metrics
            # This would require storing production model metrics
            # For now, promote if accuracy > 90%
            return metrics.get('accuracy', 0) > 0.90
            
        except Exception as e:
            logger.error(f"Error checking auto-promotion criteria: {e}")
            return False
    
    def end_experiment(self):
        """End current experiment"""
        mlflow.end_run()
        wandb.finish()
        logger.info("Experiment ended")
    
    def cleanup_old_experiments(self, days_to_keep: int = 30):
        """Clean up old experiment runs"""
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        try:
            runs = mlflow.search_runs(
                experiment_ids=[self.experiment],
                filter_string=f"attribute.start_time < '{cutoff_date.isoformat()}'",
                max_results=1000
            )
            
            for _, run in runs.iterrows():
                mlflow.delete_run(run['run_id'])
                logger.info(f"Deleted old run: {run['run_id']}")
                
        except Exception as e:
            logger.error(f"Error cleaning up old experiments: {e}")

def main():
    """Test MLOps pipeline"""
    
    # Initialize MLOps manager
    mlops = DisasterMLOpsManager()
    
    # Test experiment tracking
    config = {
        'model_type': 'text_classifier',
        'learning_rate': 0.001,
        'batch_size': 32,
        'epochs': 5
    }
    
    run_id = mlops.start_experiment("test_run", "text_classifier", config)
    
    # Test metrics logging
    test_metrics = {
        'accuracy': 0.87,
        'f1_score': 0.85,
        'precision': 0.88,
        'recall': 0.83
    }
    
    mlops.log_metrics(test_metrics)
    
    # Test model performance logging
    y_true = np.array([0, 1, 2, 0, 1, 2, 0, 1])
    y_pred = np.array([0, 1, 2, 0, 2, 2, 0, 1])
    class_names = ['no_disaster', 'flood', 'fire']
    
    mlops.log_model_performance('text_classifier', y_true, y_pred, class_names)
    
    # Test retraining decision
    recent_metrics = {'accuracy': 0.75, 'f1_score': 0.72}
    should_retrain = mlops.should_retrain('text_classifier', recent_metrics)
    print(f"Should retrain: {should_retrain}")
    
    mlops.end_experiment()
    
    print("MLOps pipeline test completed")

if __name__ == "__main__":
    main()