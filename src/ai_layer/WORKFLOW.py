"""
ML Model Workflow - Complete Pipeline

This file documents the complete workflow for training, evaluating,
and deploying the intent inference model.
"""

# ==============================================================================
# WORKFLOW STEPS
# ==============================================================================

"""
STEP 1: GENERATE TRAINING DATA
-------------------------------
Generates synthetic labeled dataset from flight scenarios.

Command:
    python src/ai_layer/dataset_generator.py

Input:
    - Flight scenario templates (normal, attack, edge cases)
    - Labeling rules (IntentLabeler)

Output:
    - data/intent_model/train.csv (70% of sessions)
    - data/intent_model/val.csv (15% of sessions)
    - data/intent_model/test.csv (15% of sessions)
    - data/intent_model/metadata.json

Metrics:
    - ~3000 samples from 300 flight sessions
    - Balanced class distribution
    - 30% attack samples, 70% normal operations

Time: ~2-5 minutes
"""

"""
STEP 2: TRAIN ML MODEL
----------------------
Trains LightGBM multi-output model (intent classification + risk regression).

Command:
    python src/ai_layer/train_model_v2.py

Input:
    - data/intent_model/train.csv
    - data/intent_model/val.csv

Output:
    - models/intent_model/intent_classifier.txt
    - models/intent_model/risk_regressor.txt
    - models/intent_model/model_metadata.json
    - models/intent_model/training_metrics.json
    - models/intent_model/inference_speed.json

Hyperparameters:
    - num_leaves: 31 (small tree)
    - max_depth: 8
    - n_estimators: 100
    - Optimized for inference speed (<10ms)

Metrics:
    - Intent Precision: >75% (target)
    - Risk MAE: <0.1 (target)
    - Training time: ~1-3 minutes

Time: ~1-3 minutes
"""

"""
STEP 3: EVALUATE MODEL
----------------------
Comprehensive evaluation on test set.

Command:
    python src/ai_layer/model_evaluation.py

Input:
    - models/intent_model/ (trained models)
    - data/intent_model/test.csv

Output:
    - models/intent_model/evaluation_report.json

Evaluated Metrics:
    ✓ Per-class precision, recall, F1
    ✓ False positive rate (target <5%)
    ✓ Inference latency (target P95 <10ms)
    ✓ Explainability completeness (target >80%)
    ✓ Attack detection rate (target >80%)
    ✓ Edge case handling

Production Readiness Criteria:
    - All targets met → Production ready ✅
    - Any target failed → Blockers identified ❌

Time: ~2-5 minutes
"""

"""
STEP 4: INTEGRATION TESTING
---------------------------
End-to-end pipeline testing with decision engine.

Command:
    python src/ai_layer/integration_example.py

Scenarios:
    1. Normal navigation command
    2. High-risk attack (MITM disarm at altitude)
    3. ML model fallback (low confidence)

Validates:
    - Feature extraction → ML inference → Decision engine flow
    - SHAP explainability output
    - Fail-safe behavior
    - Latency <50ms end-to-end

Time: <1 minute
"""

"""
STEP 5: DEPLOYMENT
------------------
Model is now ready for production deployment.

Integration Points:
    1. Feature Extraction:
       - FeatureExtractorV2 processes MAVLink commands
       - Maintains temporal window (7 commands)
       - Outputs 37-dim feature vector

    2. ML Inference:
       - IntentInferenceEngine loads models
       - Runs inference with SHAP explainability
       - Returns intent, confidence, risk, features

    3. Decision Engine:
       - RiskProportionalDecisionEngine consumes ML output
       - Weights ML risk (20%) with other layers
       - Makes final decision (ACCEPT/CONSTRAIN/HOLD/RTL)

    4. Logging:
       - Explainable logger records ML explanations
       - Decision trail includes SHAP values
       - Audit trail for post-incident analysis

File Locations:
    - Models: models/intent_model/
    - Code: src/ai_layer/
    - Logs: logs/decision_log.jsonl
"""

# ==============================================================================
# USAGE IN PRODUCTION
# ==============================================================================

"""
PRODUCTION INFERENCE EXAMPLE
----------------------------
"""

from src.ai_layer.feature_extractor_v2 import FeatureExtractorV2, mavlink_to_context
from src.ai_layer.inference_v2 import get_inference_engine
from src.decision_engine.decision_engine import RiskProportionalDecisionEngine

# Initialize components (once at startup)
feature_extractor = FeatureExtractorV2(window_size=7)
ml_engine = get_inference_engine(
    model_dir="models/intent_model",
    confidence_threshold=0.6,
    enable_shap=True
)
decision_engine = RiskProportionalDecisionEngine(
    config={'use_ml_intent': True}
)

# Per-command inference
def process_command(mavlink_msg, vehicle_state, crypto_valid, intent_result, 
                   behavior_result, shadow_result):
    """Process incoming MAVLink command"""
    
    # 1. Extract features
    ctx = mavlink_to_context(mavlink_msg, vehicle_state)
    features = feature_extractor.extract(ctx)
    
    # 2. ML inference (advisory)
    ml_result = None
    if features is not None:
        ml_result = ml_engine.infer(features)
    
    # 3. Decision engine (final authority)
    decision = decision_engine.decide(
        crypto_valid=crypto_valid,
        intent_result=intent_result,
        behavior_result=behavior_result,
        shadow_result=shadow_result,
        command_obj=mavlink_msg,
        ml_intent_result=ml_result  # ML advisory input
    )
    
    return decision

# ==============================================================================
# MONITORING
# ==============================================================================

"""
PRODUCTION MONITORING
--------------------

Key Metrics to Monitor:
    1. ML inference latency (P95, P99)
    2. Confidence distribution (% low confidence)
    3. Fallback rate (% failed inferences)
    4. Intent distribution (detect drift)
    5. Risk score distribution
    6. Decision overrides (ML vs rules)

Alerts:
    - Latency spike (P95 >10ms)
    - High fallback rate (>10%)
    - Intent distribution shift
    - Model degradation (accuracy drop)

Logging:
    - All ML outputs logged to logs/decision_log.jsonl
    - SHAP explanations included
    - Confidence scores tracked
    - Fallback reasons captured

Statistics:
    engine.get_statistics()
    # Returns: total_inferences, fallback_count, avg_latency, etc.
"""

# ==============================================================================
# RETRAINING
# ==============================================================================

"""
MODEL RETRAINING WORKFLOW
-------------------------

When to retrain:
    - New attack patterns observed
    - Intent distribution shift
    - False positive rate increases
    - New flight scenarios added
    - Model accuracy degrades

Retraining Steps:
    1. Collect new labeled data
       - Real flight logs
       - New attack scenarios
       - Edge cases from production
    
    2. Augment training dataset
       - Add to data/intent_model/train.csv
       - Maintain train/val/test split by session
    
    3. Retrain model
       - python src/ai_layer/train_model_v2.py
       - Compare metrics to baseline
    
    4. Evaluate new model
       - python src/ai_layer/model_evaluation.py
       - Ensure metrics not regressed
    
    5. A/B testing
       - Deploy new model to subset of flights
       - Monitor performance
    
    6. Full deployment
       - Replace models/intent_model/ with new version
       - Update model_metadata.json

Versioning:
    - models/intent_model/v1.0/
    - models/intent_model/v1.1/
    - models/intent_model/latest/ (symlink)
"""

# ==============================================================================
# SAFETY NOTES
# ==============================================================================

"""
CRITICAL SAFETY REMINDERS
-------------------------

1. MODEL DOES NOT CONTROL
   ❌ Model never blocks commands directly
   ❌ Model never triggers actuators
   ❌ Model never overrides safety logic
   ✅ Model provides advisory scores only

2. FAIL-SAFE BEHAVIOR
   - If model fails → system continues with rules
   - If confidence low → defer to rule-based logic
   - If model crashes → fail silent (not deadly)

3. CONSERVATIVE ESTIMATES
   - When uncertain → report high risk
   - ML disagrees with rules → take higher risk
   - Low confidence → conservative fallback

4. EXPLAINABILITY REQUIRED
   - Every decision must be explainable
   - SHAP values for all predictions
   - Audit trail for post-incident analysis

5. HUMAN IN THE LOOP
   - Model assists human decision-making
   - Not a replacement for safety logic
   - Operator can override ML recommendations
"""

# ==============================================================================
# TROUBLESHOOTING
# ==============================================================================

"""
COMMON ISSUES & SOLUTIONS
-------------------------

Issue: Model not loading
Solution:
    - Check models/intent_model/ exists
    - Regenerate: python src/ai_layer/train_model_v2.py
    - Verify file permissions

Issue: High latency (>10ms)
Solution:
    - Disable SHAP: enable_shap=False
    - Reduce tree count in training params
    - Check CPU load / resource contention

Issue: High fallback rate
Solution:
    - Check feature extraction (insufficient history?)
    - Verify input data quality
    - Lower confidence threshold (with caution)

Issue: Low accuracy
Solution:
    - Generate more training data
    - Add edge cases to dataset
    - Retrain with larger n_estimators
    - Check for data quality issues

Issue: Integration errors
Solution:
    - Verify decision engine weights sum to 1.0
    - Check ml_intent_result format
    - Ensure all layers provide valid output
    - Test with integration_example.py
"""

# ==============================================================================
# PERFORMANCE BENCHMARKS
# ==============================================================================

"""
EXPECTED PERFORMANCE (Raspberry Pi 4)
-------------------------------------

Inference Latency:
    - P50: ~3-5ms
    - P95: <10ms
    - P99: <15ms

Throughput:
    - ~200-300 inferences/second
    - CPU usage: <20% per core

Memory:
    - Model size: ~50KB (intent) + ~50KB (risk)
    - Runtime: ~100MB total (including SHAP)

Accuracy (Test Set):
    - Intent Precision: >75%
    - Risk MAE: <0.1
    - FPR: <5%
    - Attack Detection: >80%

End-to-End Latency:
    - Feature extraction: ~1-2ms
    - ML inference: ~3-5ms
    - SHAP computation: ~2-3ms
    - Decision engine: ~1-2ms
    - Total: <20ms
"""

# ==============================================================================
# FILE STRUCTURE
# ==============================================================================

"""
PROJECT STRUCTURE
----------------

src/ai_layer/
├── feature_extractor_v2.py      # Feature extraction (37 features)
├── intent_labels.py             # Intent classes & risk scoring
├── dataset_generator.py         # Training data generation
├── train_model_v2.py            # Model training pipeline
├── inference_v2.py              # Production inference engine
├── model_evaluation.py          # Comprehensive evaluation
└── integration_example.py       # End-to-end examples

models/intent_model/
├── intent_classifier.txt        # LightGBM intent model
├── risk_regressor.txt           # LightGBM risk model
├── model_metadata.json          # Feature schema
├── training_metrics.json        # Training performance
├── evaluation_report.json       # Test evaluation
└── inference_speed.json         # Latency benchmarks

data/intent_model/
├── train.csv                    # Training data
├── val.csv                      # Validation data
├── test.csv                     # Test data
└── metadata.json                # Dataset metadata

docs/
└── ML_INTENT_MODEL.md           # Complete documentation
"""

# ==============================================================================
# CONTACT & SUPPORT
# ==============================================================================

"""
For questions or issues:
    - Check docs/ML_INTENT_MODEL.md
    - Run integration examples
    - Review evaluation reports
    - Check decision logs

Built for HackSymmetric 2026
"""
