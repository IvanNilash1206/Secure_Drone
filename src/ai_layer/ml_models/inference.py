"""
Intent Inference Engine with SHAP Explainability

CRITICAL SAFETY PRINCIPLES:
1. Model ADVISES - it does NOT control motors or block commands
2. Model output is ONE INPUT to decision engine
3. If model fails → fail silent (not fail deadly)
4. If confidence low → defer to rules
5. If model disagrees with rules → take higher risk

Outputs:
{
  "intent": "ABORT",
  "confidence": 0.87,
  "intent_risk": 0.78,
  "top_features": ["mission_phase", "command_type"],
  "shap_explanation": {...}
}
"""

import numpy as np
import lightgbm as lgb
import shap
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from src.ai_layer.intent_labels import IntentClass, RiskLevel


@dataclass
class IntentInferenceResult:
    """
    Complete inference output for decision engine
    
    This is the contract between ML model and decision engine
    """
    # Primary outputs
    intent: str                    # Intent class name (e.g., "NAVIGATION")
    confidence: float              # Model confidence [0, 1]
    intent_risk: float             # Contextual risk score [0, 1]
    
    # Explainability
    top_features: List[str]        # Top N contributing features
    feature_contributions: Dict[str, float]  # SHAP values
    
    # Metadata
    inference_time_ms: float       # Latency
    model_status: str              # "OK" | "LOW_CONFIDENCE" | "FALLBACK"
    fallback_reason: Optional[str] # Why fallback triggered (if any)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class IntentInferenceEngine:
    """
    Production inference engine with SHAP explainability
    
    Features:
    - Fast inference (<10ms)
    - Deterministic predictions
    - Per-decision explanations via SHAP
    - Confidence scoring
    - Graceful fallback on failures
    - Fail-silent behavior
    """
    
    def __init__(self, 
                 model_dir: str = "models/intent_model",
                 confidence_threshold: float = 0.6,
                 enable_shap: bool = True):
        """
        Args:
            model_dir: Path to saved models
            confidence_threshold: Minimum confidence to trust prediction
            enable_shap: Whether to compute SHAP values (adds ~2ms latency)
        """
        self.model_dir = Path(model_dir)
        self.confidence_threshold = confidence_threshold
        self.enable_shap = enable_shap
        
        # Load models
        self.intent_classifier = None
        self.risk_regressor = None
        self.feature_names = None
        self.n_classes = 9
        
        # SHAP explainers
        self.intent_explainer = None
        self.risk_explainer = None
        
        # Statistics
        self.inference_count = 0
        self.fallback_count = 0
        self.total_inference_time_ms = 0.0
        
        # Load models on initialization
        self._load_models()
        
        if self.enable_shap:
            self._initialize_shap()
        
        print(f"✅ IntentInferenceEngine initialized")
        print(f"   Confidence threshold: {self.confidence_threshold}")
        print(f"   SHAP explainability: {'Enabled' if self.enable_shap else 'Disabled'}")
    
    def _load_models(self):
        """Load trained models from disk"""
        try:
            classifier_path = self.model_dir / 'intent_classifier.txt'
            regressor_path = self.model_dir / 'risk_regressor.txt'
            metadata_path = self.model_dir / 'model_metadata.json'
            
            if not classifier_path.exists():
                raise FileNotFoundError(f"Classifier not found: {classifier_path}")
            if not regressor_path.exists():
                raise FileNotFoundError(f"Regressor not found: {regressor_path}")
            
            # Load LightGBM models
            self.intent_classifier = lgb.Booster(model_file=str(classifier_path))
            self.risk_regressor = lgb.Booster(model_file=str(regressor_path))
            
            # Load metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                self.feature_names = metadata['feature_names']
                self.n_classes = metadata['n_classes']
            
            print(f"   ✓ Models loaded from {self.model_dir}")
            
        except Exception as e:
            print(f"   ✗ CRITICAL: Failed to load models: {e}")
            print(f"   → Model will operate in FALLBACK mode")
            self.intent_classifier = None
            self.risk_regressor = None
    
    def _initialize_shap(self):
        """Initialize SHAP explainers (compute-intensive, do once)"""
        try:
            # Create small background dataset for SHAP
            # (use representative samples, not full training set)
            background = np.random.rand(100, len(self.feature_names)).astype(np.float32)
            
            # TreeExplainer for LightGBM (fast, exact)
            self.intent_explainer = shap.TreeExplainer(self.intent_classifier)
            self.risk_explainer = shap.TreeExplainer(self.risk_regressor)
            
            print(f"   ✓ SHAP explainers initialized")
            
        except Exception as e:
            print(f"   ✗ SHAP initialization failed: {e}")
            print(f"   → Explainability will be limited to feature importance")
            self.intent_explainer = None
            self.risk_explainer = None
    
    def infer(self, feature_vector: np.ndarray) -> IntentInferenceResult:
        """
        Perform intent inference with explainability
        
        Args:
            feature_vector: 37-dim feature array from FeatureExtractorV2
            
        Returns:
            IntentInferenceResult with intent, risk, and explanations
        """
        start_time = time.perf_counter()
        
        # Validate input
        if feature_vector is None:
            return self._fallback_result("Insufficient feature history")
        
        if len(feature_vector) != len(self.feature_names):
            return self._fallback_result(f"Feature dimension mismatch: expected {len(self.feature_names)}, got {len(feature_vector)}")
        
        # Check if models loaded
        if self.intent_classifier is None or self.risk_regressor is None:
            return self._fallback_result("Models not loaded")
        
        try:
            # Reshape for model input
            X = feature_vector.reshape(1, -1).astype(np.float32)
            
            # 1. Predict intent
            intent_probs = self.intent_classifier.predict(X)[0]
            intent_idx = int(np.argmax(intent_probs))
            intent_confidence = float(intent_probs[intent_idx])
            intent_class = IntentClass.from_index(intent_idx)
            
            # 2. Predict risk
            risk_score = float(self.risk_regressor.predict(X)[0])
            risk_score = np.clip(risk_score, 0.0, 1.0)
            
            # 3. Check confidence threshold
            if intent_confidence < self.confidence_threshold:
                return self._fallback_result(
                    f"Low confidence: {intent_confidence:.2f} < {self.confidence_threshold}",
                    partial_intent=intent_class.value,
                    partial_risk=risk_score
                )
            
            # 4. Compute SHAP explanations
            if self.enable_shap and self.intent_explainer is not None:
                shap_values = self._compute_shap_values(X, intent_idx)
            else:
                # Fallback to feature importance
                shap_values = self._get_feature_importance()
            
            # 5. Extract top features
            top_features, feature_contributions = self._extract_top_features(shap_values, n=5)
            
            # Measure latency
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Update statistics
            self.inference_count += 1
            self.total_inference_time_ms += inference_time_ms
            
            # Build result
            result = IntentInferenceResult(
                intent=intent_class.value,
                confidence=intent_confidence,
                intent_risk=risk_score,
                top_features=top_features,
                feature_contributions=feature_contributions,
                inference_time_ms=inference_time_ms,
                model_status="OK",
                fallback_reason=None
            )
            
            return result
            
        except Exception as e:
            # FAIL SILENT: Return fallback result
            print(f"⚠️  Inference error: {e}")
            return self._fallback_result(f"Inference exception: {str(e)}")
    
    def _compute_shap_values(self, X: np.ndarray, intent_idx: int) -> Dict[str, float]:
        """
        Compute SHAP values for feature contributions
        
        Returns dict of {feature_name: contribution_value}
        """
        try:
            # Compute SHAP values for intent prediction
            shap_values = self.intent_explainer.shap_values(X)
            
            # Extract values for predicted class
            if isinstance(shap_values, list):
                # Multi-class: list of arrays
                class_shap = shap_values[intent_idx][0]
            else:
                # Single array
                class_shap = shap_values[0]
            
            # Map to feature names
            contributions = {
                self.feature_names[i]: float(class_shap[i])
                for i in range(len(self.feature_names))
            }
            
            return contributions
            
        except Exception as e:
            print(f"SHAP computation failed: {e}")
            return self._get_feature_importance()
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """Fallback: Use global feature importance instead of SHAP"""
        importance = self.intent_classifier.feature_importance(importance_type='gain')
        return {
            self.feature_names[i]: float(importance[i])
            for i in range(len(self.feature_names))
        }
    
    def _extract_top_features(self, 
                            contributions: Dict[str, float],
                            n: int = 5) -> tuple:
        """
        Extract top N contributing features
        
        Returns:
            (feature_names_list, contributions_dict)
        """
        # Sort by absolute contribution
        sorted_features = sorted(
            contributions.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        top_n = sorted_features[:n]
        top_names = [name for name, _ in top_n]
        top_dict = {name: val for name, val in top_n}
        
        return top_names, top_dict
    
    def _fallback_result(self, 
                        reason: str,
                        partial_intent: Optional[str] = None,
                        partial_risk: Optional[float] = None) -> IntentInferenceResult:
        """
        Generate fallback result when model cannot make confident prediction
        
        SAFETY: Fail gracefully, provide minimal info to decision engine
        """
        self.fallback_count += 1
        
        return IntentInferenceResult(
            intent=partial_intent if partial_intent else "UNKNOWN",
            confidence=0.0,  # Zero confidence → decision engine uses rules
            intent_risk=partial_risk if partial_risk else 0.8,  # Conservative high risk
            top_features=[],
            feature_contributions={},
            inference_time_ms=0.0,
            model_status="FALLBACK",
            fallback_reason=reason
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Return inference statistics for monitoring"""
        if self.inference_count > 0:
            avg_time = self.total_inference_time_ms / self.inference_count
        else:
            avg_time = 0.0
        
        return {
            'total_inferences': self.inference_count,
            'fallback_count': self.fallback_count,
            'fallback_rate': self.fallback_count / max(1, self.inference_count),
            'avg_inference_time_ms': avg_time,
            'shap_enabled': self.enable_shap,
            'confidence_threshold': self.confidence_threshold,
        }
    
    def reset_statistics(self):
        """Reset inference counters"""
        self.inference_count = 0
        self.fallback_count = 0
        self.total_inference_time_ms = 0.0


# Module-level singleton instance (lazy initialization)
_engine_instance = None


def get_inference_engine(model_dir: str = "models/intent_model",
                        confidence_threshold: float = 0.6,
                        enable_shap: bool = True) -> IntentInferenceEngine:
    """
    Get singleton inference engine instance
    
    This ensures models are loaded only once
    """
    global _engine_instance
    
    if _engine_instance is None:
        _engine_instance = IntentInferenceEngine(
            model_dir=model_dir,
            confidence_threshold=confidence_threshold,
            enable_shap=enable_shap
        )
    
    return _engine_instance


if __name__ == "__main__":
    # Test inference engine
    print("🧪 Testing IntentInferenceEngine...\n")
    
    # Initialize engine
    engine = IntentInferenceEngine(
        model_dir="models/intent_model",
        confidence_threshold=0.6,
        enable_shap=True
    )
    
    # Generate test feature vector (37 features)
    test_features = np.random.rand(37).astype(np.float32)
    
    # Run inference
    print("Running inference...")
    result = engine.infer(test_features)
    
    print("\n📊 Inference Result:")
    print(f"   Intent: {result.intent}")
    print(f"   Confidence: {result.confidence:.3f}")
    print(f"   Risk Score: {result.intent_risk:.3f}")
    print(f"   Status: {result.model_status}")
    print(f"   Inference Time: {result.inference_time_ms:.2f}ms")
    
    if result.top_features:
        print(f"\n   Top Contributing Features:")
        for i, feat in enumerate(result.top_features, 1):
            contrib = result.feature_contributions.get(feat, 0.0)
            print(f"      {i}. {feat}: {contrib:.3f}")
    
    if result.fallback_reason:
        print(f"\n   ⚠️  Fallback Reason: {result.fallback_reason}")
    
    # Statistics
    print("\n" + "="*60)
    print("📈 Engine Statistics:")
    stats = engine.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Inference engine test complete!")
    
    # JSON output (for integration testing)
    print("\n📤 JSON Output (for decision engine):")
    print(result.to_json())
