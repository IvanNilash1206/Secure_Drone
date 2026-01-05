"""
Intent Inference Model Training

Multi-output model:
1. Intent classification (9 classes)
2. Risk score regression [0, 1]

Model: LightGBM (fast CPU inference, deterministic, explainable)
Explainability: SHAP values
Target: <10ms inference on Raspberry Pi

Safety: Model advises, does NOT control
"""

import numpy as np
import pandas as pd
import lightgbm as lgb
import joblib
import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error
)

from src.ai_layer.intent_labels import IntentClass


class IntentModelTrainer:
    """
    Trains multi-output intent inference model
    
    Architecture:
    - Two separate LightGBM models (one for classification, one for regression)
    - Optimized for inference speed
    - Deterministic predictions
    - Full SHAP explainability
    """
    
    def __init__(self, model_dir: str = "models/intent_model"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.intent_classifier = None
        self.risk_regressor = None
        self.feature_names = None
        self.n_classes = 9  # IntentClass enum size
        
    def train(self, 
             train_df: pd.DataFrame,
             val_df: pd.DataFrame,
             optimize_for: str = 'inference_speed') -> Dict[str, Any]:
        """
        Train intent classifier + risk regressor
        
        Args:
            train_df: Training data with features + labels
            val_df: Validation data
            optimize_for: 'inference_speed' or 'accuracy'
            
        Returns:
            Training metrics dict
        """
        print("🚂 Training intent inference model...")
        
        # Extract features and labels
        feature_cols = [c for c in train_df.columns if c.startswith('feature_')]
        self.feature_names = feature_cols
        
        X_train = train_df[feature_cols].values
        y_intent_train = train_df['intent_index'].values
        y_risk_train = train_df['risk_score'].values
        
        X_val = val_df[feature_cols].values
        y_intent_val = val_df['intent_index'].values
        y_risk_val = val_df['risk_score'].values
        
        print(f"Training data: {X_train.shape[0]} samples, {X_train.shape[1]} features")
        print(f"Validation data: {X_val.shape[0]} samples")
        
        # Train intent classifier
        print("\n1️⃣ Training intent classifier...")
        classifier_metrics = self._train_intent_classifier(
            X_train, y_intent_train,
            X_val, y_intent_val,
            optimize_for
        )
        
        # Train risk regressor
        print("\n2️⃣ Training risk regressor...")
        regressor_metrics = self._train_risk_regressor(
            X_train, y_risk_train,
            X_val, y_risk_val,
            optimize_for
        )
        
        # Save models
        self._save_models()
        
        # Combined metrics
        metrics = {
            'classifier': classifier_metrics,
            'regressor': regressor_metrics,
            'training_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Save metrics
        with open(self.model_dir / 'training_metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"\n✅ Training complete. Models saved to {self.model_dir}")
        
        return metrics
    
    def _train_intent_classifier(self,
                                 X_train, y_train,
                                 X_val, y_val,
                                 optimize_for: str) -> Dict[str, Any]:
        """Train LightGBM classifier for intent prediction"""
        
        # Hyperparameters optimized for inference speed
        if optimize_for == 'inference_speed':
            params = {
                'objective': 'multiclass',
                'num_class': self.n_classes,
                'metric': 'multi_logloss',
                'boosting_type': 'gbdt',
                'num_leaves': 31,          # Small tree
                'max_depth': 8,            # Shallow depth
                'learning_rate': 0.05,
                'n_estimators': 100,       # Few trees = fast inference
                'min_child_samples': 20,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'reg_alpha': 0.1,
                'reg_lambda': 0.1,
                'random_state': 42,
                'verbose': -1,
                'deterministic': True,     # Deterministic inference
            }
        else:
            params = {
                'objective': 'multiclass',
                'num_class': self.n_classes,
                'metric': 'multi_logloss',
                'boosting_type': 'gbdt',
                'num_leaves': 63,
                'max_depth': 12,
                'learning_rate': 0.03,
                'n_estimators': 300,
                'min_child_samples': 10,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'reg_alpha': 0.1,
                'reg_lambda': 0.1,
                'random_state': 42,
                'verbose': -1,
                'deterministic': True,
            }
        
        # Create datasets
        train_data = lgb.Dataset(X_train, label=y_train, feature_name=self.feature_names)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data, feature_name=self.feature_names)
        
        # Train with early stopping
        callbacks = [
            lgb.early_stopping(stopping_rounds=20, verbose=False),
            lgb.log_evaluation(period=50)
        ]
        
        self.intent_classifier = lgb.train(
            params,
            train_data,
            valid_sets=[train_data, val_data],
            valid_names=['train', 'val'],
            callbacks=callbacks
        )
        
        # Evaluate
        y_pred = self.intent_classifier.predict(X_val, num_iteration=self.intent_classifier.best_iteration)
        y_pred_class = np.argmax(y_pred, axis=1)
        
        # Per-class metrics
        intent_names = [IntentClass.from_index(i).value for i in range(self.n_classes)]
        report = classification_report(y_val, y_pred_class, target_names=intent_names, output_dict=True)
        
        # Overall metrics
        precision = precision_score(y_val, y_pred_class, average='weighted')
        recall = recall_score(y_val, y_pred_class, average='weighted')
        f1 = f1_score(y_val, y_pred_class, average='weighted')
        
        print(f"   Precision: {precision:.3f}")
        print(f"   Recall: {recall:.3f}")
        print(f"   F1: {f1:.3f}")
        print(f"   Best iteration: {self.intent_classifier.best_iteration}")
        
        # Feature importance
        importance = self.intent_classifier.feature_importance(importance_type='gain')
        top_features = sorted(zip(self.feature_names, importance), key=lambda x: x[1], reverse=True)[:10]
        
        print("\n   Top 10 features:")
        for feat, imp in top_features:
            print(f"      {feat}: {imp:.0f}")
        
        return {
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'n_estimators': self.intent_classifier.best_iteration,
            'classification_report': report,
            'confusion_matrix': confusion_matrix(y_val, y_pred_class).tolist(),
            'top_features': [(feat, float(imp)) for feat, imp in top_features],
        }
    
    def _train_risk_regressor(self,
                             X_train, y_train,
                             X_val, y_val,
                             optimize_for: str) -> Dict[str, Any]:
        """Train LightGBM regressor for risk score prediction"""
        
        # Hyperparameters
        if optimize_for == 'inference_speed':
            params = {
                'objective': 'regression',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'max_depth': 8,
                'learning_rate': 0.05,
                'n_estimators': 100,
                'min_child_samples': 20,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'reg_alpha': 0.1,
                'reg_lambda': 0.1,
                'random_state': 42,
                'verbose': -1,
                'deterministic': True,
            }
        else:
            params = {
                'objective': 'regression',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'num_leaves': 63,
                'max_depth': 12,
                'learning_rate': 0.03,
                'n_estimators': 300,
                'min_child_samples': 10,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'reg_alpha': 0.1,
                'reg_lambda': 0.1,
                'random_state': 42,
                'verbose': -1,
                'deterministic': True,
            }
        
        # Create datasets
        train_data = lgb.Dataset(X_train, label=y_train, feature_name=self.feature_names)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data, feature_name=self.feature_names)
        
        # Train
        callbacks = [
            lgb.early_stopping(stopping_rounds=20, verbose=False),
            lgb.log_evaluation(period=50)
        ]
        
        self.risk_regressor = lgb.train(
            params,
            train_data,
            valid_sets=[train_data, val_data],
            valid_names=['train', 'val'],
            callbacks=callbacks
        )
        
        # Evaluate
        y_pred = self.risk_regressor.predict(X_val, num_iteration=self.risk_regressor.best_iteration)
        y_pred = np.clip(y_pred, 0.0, 1.0)  # Clamp to [0, 1]
        
        mae = mean_absolute_error(y_val, y_pred)
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))
        
        print(f"   MAE: {mae:.3f}")
        print(f"   RMSE: {rmse:.3f}")
        print(f"   Best iteration: {self.risk_regressor.best_iteration}")
        
        # Feature importance
        importance = self.risk_regressor.feature_importance(importance_type='gain')
        top_features = sorted(zip(self.feature_names, importance), key=lambda x: x[1], reverse=True)[:10]
        
        print("\n   Top 10 features:")
        for feat, imp in top_features:
            print(f"      {feat}: {imp:.0f}")
        
        return {
            'mae': float(mae),
            'rmse': float(rmse),
            'n_estimators': self.risk_regressor.best_iteration,
            'top_features': [(feat, float(imp)) for feat, imp in top_features],
        }
    
    def _save_models(self):
        """Save trained models to disk"""
        # Save LightGBM models (native format for fast loading)
        self.intent_classifier.save_model(str(self.model_dir / 'intent_classifier.txt'))
        self.risk_regressor.save_model(str(self.model_dir / 'risk_regressor.txt'))
        
        # Save metadata
        metadata = {
            'feature_names': self.feature_names,
            'n_features': len(self.feature_names),
            'n_classes': self.n_classes,
            'intent_classes': [IntentClass.from_index(i).value for i in range(self.n_classes)],
            'model_type': 'LightGBM',
            'saved_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        with open(self.model_dir / 'model_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n💾 Models saved:")
        print(f"   - {self.model_dir / 'intent_classifier.txt'}")
        print(f"   - {self.model_dir / 'risk_regressor.txt'}")
        print(f"   - {self.model_dir / 'model_metadata.json'}")


def benchmark_inference_speed(model_dir: str = "models/intent_model",
                              n_samples: int = 1000) -> Dict[str, float]:
    """
    Benchmark model inference speed
    
    Target: <10ms per inference on Raspberry Pi
    """
    print(f"\n⚡ Benchmarking inference speed ({n_samples} samples)...")
    
    # Load models
    classifier = lgb.Booster(model_file=f"{model_dir}/intent_classifier.txt")
    regressor = lgb.Booster(model_file=f"{model_dir}/risk_regressor.txt")
    
    # Generate random input (37 features)
    X = np.random.rand(n_samples, 37).astype(np.float32)
    
    # Warm-up (compile)
    _ = classifier.predict(X[:10])
    _ = regressor.predict(X[:10])
    
    # Benchmark intent classification
    start = time.perf_counter()
    intent_preds = classifier.predict(X)
    intent_time = (time.perf_counter() - start) * 1000  # ms
    
    # Benchmark risk regression
    start = time.perf_counter()
    risk_preds = regressor.predict(X)
    risk_time = (time.perf_counter() - start) * 1000  # ms
    
    # Total inference time
    total_time = intent_time + risk_time
    per_sample_time = total_time / n_samples
    throughput = n_samples / (total_time / 1000)  # samples/sec
    
    print(f"\n📊 Inference speed results:")
    print(f"   Intent classification: {intent_time:.2f}ms total ({intent_time/n_samples:.3f}ms per sample)")
    print(f"   Risk regression: {risk_time:.2f}ms total ({risk_time/n_samples:.3f}ms per sample)")
    print(f"   Combined: {per_sample_time:.3f}ms per sample")
    print(f"   Throughput: {throughput:.0f} samples/second")
    
    if per_sample_time < 10.0:
        print(f"   ✅ PASS: <10ms target met!")
    else:
        print(f"   ⚠️  WARN: Exceeds 10ms target (optimize model)")
    
    return {
        'intent_time_ms': intent_time,
        'risk_time_ms': risk_time,
        'total_time_ms': total_time,
        'per_sample_ms': per_sample_time,
        'throughput_samples_per_sec': throughput,
        'meets_10ms_target': per_sample_time < 10.0,
    }


if __name__ == "__main__":
    # Load dataset
    data_dir = Path("data/intent_model")
    
    print("📂 Loading training data...")
    train_df = pd.read_csv(data_dir / 'train.csv')
    val_df = pd.read_csv(data_dir / 'val.csv')
    test_df = pd.read_csv(data_dir / 'test.csv')
    
    print(f"   Train: {len(train_df)} samples")
    print(f"   Val: {len(val_df)} samples")
    print(f"   Test: {len(test_df)} samples")
    
    # Train model
    trainer = IntentModelTrainer(model_dir="models/intent_model")
    metrics = trainer.train(train_df, val_df, optimize_for='inference_speed')
    
    print("\n" + "="*60)
    print("📈 TRAINING SUMMARY")
    print("="*60)
    print(f"\nIntent Classifier:")
    print(f"   Precision: {metrics['classifier']['precision']:.3f}")
    print(f"   Recall: {metrics['classifier']['recall']:.3f}")
    print(f"   F1: {metrics['classifier']['f1_score']:.3f}")
    
    print(f"\nRisk Regressor:")
    print(f"   MAE: {metrics['regressor']['mae']:.3f}")
    print(f"   RMSE: {metrics['regressor']['rmse']:.3f}")
    
    # Benchmark inference speed
    speed_metrics = benchmark_inference_speed(model_dir="models/intent_model")
    
    # Save speed metrics
    with open("models/intent_model/inference_speed.json", 'w') as f:
        json.dump(speed_metrics, f, indent=2)
    
    print("\n✅ Training and benchmarking complete!")
