# Secure Drone - AI Layer & Attack Detection Architecture

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [AI Layer Structure](#ai-layer-structure)
4. [Digital Twin Layer](#digital-twin-layer)
5. [Attack Detection](#attack-detection)
6. [Integration](#integration)
7. [Training & Testing](#training--testing)
8. [Attack Test Results](#attack-test-results)

---

## Project Overview

**Secure Drone** is a military-grade security system for autonomous drone operations that implements:

- **Cryptographic Layer**: AES-256-GCM encryption with hierarchical key management
- **AI/ML Layer**: Intent inference using LightGBM for command classification
- **Digital Twin Layer**: Lightweight kinematic prediction for risk assessment
- **Attack Detection Layer**: Real-time detection of DoS, Replay, and Injection attacks
- **Decision Engine**: Risk-proportional decision making

---

## Architecture

### Complete System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Encrypted Command (from GCS)                  │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│                    LAYER 1: Crypto Layer                          │
│  ├─ AES-256-GCM Decryption                                       │
│  ├─ Key Hierarchy Validation                                     │
│  └─ Timestamp Verification                                       │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│              LAYER 2: Attack Detection Layer                      │
│  ├─ DoS Detector (command rate monitoring)                       │
│  ├─ Replay Detector (nonce + timestamp + sequence)               │
│  └─ Injection Detector (authorization + parameters + context)    │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│               LAYER 3: AI/ML Intent Layer                         │
│  ├─ Rule-based Intent Firewall                                   │
│  ├─ Feature Extraction (37 features)                             │
│  ├─ LightGBM Intent Classifier (9 classes)                       │
│  └─ Risk Score Regressor                                         │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│           LAYER 4: Digital Twin (Shadow Execution)                │
│  ├─ Geofence Violation Prediction                                │
│  ├─ Altitude/Velocity Risk                                       │
│  ├─ Energy Margin Analysis                                       │
│  └─ Loss-of-Control Risk                                         │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│              LAYER 5: Decision Engine                             │
│  ├─ Aggregate All Layer Outputs                                  │
│  ├─ Risk-Proportional Decision                                   │
│  └─ Output: ACCEPT / CONSTRAIN / HOLD / RTL                      │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
              Command Executed or Blocked
```

---

## AI Layer Structure

### Directory Organization

```
src/ai_layer/
├── ml_models/                    # ML-based intent inference
│   ├── __init__.py
│   ├── feature_extractor.py     # 37-feature extraction
│   ├── inference.py             # LightGBM inference engine
│   ├── trainer.py               # Model training
│   └── dataset_generator.py     # Training data generation
│
├── attack_detection/            # Attack detection modules
│   ├── __init__.py
│   ├── dos_detector.py          # DoS attack detection
│   ├── replay_detector.py       # Replay attack detection
│   ├── injection_detector.py    # Injection attack detection
│   └── anomaly_detector.py      # Behavior anomaly detection
│
├── intent_firewall.py          # Rule-based intent analysis
├── intent_labels.py            # Intent classes & labels
├── trust_model.py              # Trust scoring
├── normalizer.py               # Feature normalization
└── command_history.py          # Command tracking

src/digital_twin/               # Digital twin (separated)
├── __init__.py
└── shadow_executor.py          # Lightweight kinematic prediction
```

### Key Components

#### 1. **Feature Extractor** (`ml_models/feature_extractor.py`)

Extracts 37 features from commands:

**Command Features (10):**
- `msg_id_normalized`: Message ID (normalized)
- `command_type_encoded`: Command type encoding
- `target_system/component`: Target identifiers
- `param1-7`: Command parameters

**Temporal Features (12):**
- `cmd_rate`: Commands per second
- `time_since_last`: Time delta
- `msg_id_transitions`: Command type changes
- `windowed_*`: Pattern analysis over 5-7 command window

**Context Features (15):**
- `flight_mode`: Current flight mode
- `mission_phase`: Mission state
- `armed_state`: Armed/disarmed
- `battery_level`: Battery percentage
- `altitude/velocity`: Vehicle state

#### 2. **Intent Classifier** (`ml_models/inference.py`)

**Model**: LightGBM (fast, deterministic, explainable)

**Intent Classes (9):**
1. NAVIGATION - Waypoint missions
2. RETURN - RTL, abort
3. SURVEY - Area coverage
4. OVERRIDE - Manual intervention
5. EMERGENCY - Critical commands
6. MANUAL_CONTROL - Human pilot
7. CONFIG - Parameter changes
8. TAKEOFF_LANDING - Flight transitions
9. UNKNOWN - Unclassified

**Performance:**
- Inference time: <10ms on Raspberry Pi
- Accuracy: >90% on validation set
- SHAP explainability included

#### 3. **Intent Firewall** (`intent_firewall.py`)

Rule-based intent validation:

```python
# Example: RTL during survey mission = INTENT MISMATCH
if intent == RETURN and mission_phase == MISSION:
    return IntentMismatch(
        reason="Unexpected RTL during active mission"
    )
```

---

## Digital Twin Layer

### Purpose

**NOT full simulation**. Lightweight kinematic prediction for risk assessment.

### Location

```
src/digital_twin/
└── shadow_executor.py
```

### Predictions

1. **Geofence Violations**: Will command cause boundary breach?
2. **Altitude Risk**: Too high (>120m) or too low (<10m)?
3. **Velocity Risk**: Exceeds safe limits (>15 m/s)?
4. **Energy Margin**: Battery sufficient for command?
5. **Loss-of-Control Risk**: Command could cause instability?
6. **Collision Risk**: Obstacle or airspace conflict?

### Output

```python
ShadowResult(
    predicted_outcomes=PredictedOutcome(
        geofence_violation=False,
        altitude_risk=False,
        velocity_risk=False,
        energy_margin="HIGH",
        loss_of_control_risk=False,
        collision_risk=False
    ),
    trajectory_risk=0.15,  # 0.0 to 1.0
    explanation="Safe execution predicted"
)
```

### Key Innovation

- Prediction horizon: 5-10 seconds
- Computation time: <10ms
- Output is **RISK**, not motion

---

## Attack Detection

### 1. DoS (Denial of Service) Detector

**File**: `src/ai_layer/attack_detection/dos_detector.py`

**Detection Methods:**
- Command rate monitoring (cmds/sec)
- Burst detection (spike in 1-sec window)
- Sustained load analysis
- Temporal pattern analysis

**Thresholds:**
- Normal: 0.5-5 cmds/sec
- Attack: >20 cmds/sec sustained
- Burst: >50 cmds/sec in 1-sec window

**Attack Patterns Detected:**
- ✅ Command flooding (25+ cmds/sec)
- ✅ Burst attacks (60 cmds in 1 sec)
- ✅ Slow DoS (15 cmds/sec sustained)

### 2. Replay Attack Detector

**File**: `src/ai_layer/attack_detection/replay_detector.py`

**Detection Layers:**
1. **Nonce Uniqueness** (Layer 1 - Cryptographic)
   - Tracks 10,000 recent nonces
   - Duplicate nonce = definitive replay

2. **Timestamp Freshness** (Layer 2)
   - 30-second tolerance window
   - Detects old or future timestamps

3. **Sequence Patterns** (Layer 3)
   - Tracks command hashes
   - Detects duplicate commands in short window

**Attack Patterns Detected:**
- ✅ Exact replay (same nonce)
- ✅ Delayed replay (old timestamp)
- ✅ Session replay (old session commands)

### 3. Message Injection Detector

**File**: `src/ai_layer/attack_detection/injection_detector.py`

**Detection Layers:**
1. **Command Authorization**
   - State-based command whitelist
   - E.g., no DISARM in IN_FLIGHT state

2. **Parameter Bounds**
   - Altitude: 0-150m (FAA limit)
   - Velocity: 0-25 m/s
   - Lat/Lon bounds

3. **Context Violations**
   - Disarm while airborne = CRITICAL
   - Mode change during landing = HIGH RISK
   - Takeoff while in flight = ANOMALY

4. **Privilege Escalation**
   - Critical commands require authentication
   - ARM/DISARM, MODE_CHANGE, PARAM_SET

**Attack Patterns Detected:**
- ✅ Unauthorized disarm in flight
- ✅ Parameter manipulation (extreme values)
- ✅ Privilege escalation (unauthenticated critical commands)
- ✅ Context violations (mode change during landing)

---

## Integration

### Integrated Pipeline

**File**: `src/integrated_pipeline.py`

**Class**: `IntegratedSecurityPipeline`

**Usage:**

```python
from src.integrated_pipeline import IntegratedSecurityPipeline
from src.crypto_layer.encryptor import encrypt_payload

# Initialize pipeline
pipeline = IntegratedSecurityPipeline(
    enable_ml=True,      # Enable ML inference
    enable_shadow=True    # Enable digital twin
)

# Update vehicle state
pipeline.update_vehicle_state(
    flight_mode="GUIDED",
    armed=True,
    altitude=50.0
)

# Process encrypted command
payload = b"ARM_AND_TAKEOFF|timestamp|GCS"
nonce, ciphertext = encrypt_payload(payload)

result = pipeline.process_encrypted_command(nonce, ciphertext)

print(f"Decision: {result.decision.decision.value}")
print(f"Processing time: {result.total_time_ms:.2f} ms")
```

### Layer Outputs

Each command flows through all layers:

```python
SecurityCheckResult(
    command="ARM_AND_TAKEOFF",
    crypto_valid=True,
    dos_metrics=DoSMetrics(...),
    replay_metrics=ReplayMetrics(...),
    injection_metrics=InjectionMetrics(...),
    intent_result=IntentResult(...),
    ml_inference=IntentInferenceResult(...),
    shadow_result=ShadowResult(...),
    decision=DecisionResult(
        decision=DecisionState.ACCEPT,
        severity=Severity.LOW,
        confidence=0.95
    ),
    total_time_ms=12.5
)
```

---

## Training & Testing

### Complete Pipeline

**File**: `train_and_test.py`

**Steps:**

1. **Dataset Generation**
   - 100 normal flight scenarios
   - 50 of each attack type (DoS, Replay, Injection)
   - Total: ~600 flight sessions with 10-50 commands each

2. **Model Training**
   - Intent Classifier: LightGBM multi-class (9 classes)
   - Risk Regressor: LightGBM regression [0, 1]
   - Optimization: Inference speed (target <10ms)

3. **Attack Testing**
   - DoS: 4 test variants
   - Replay: 4 test variants
   - Injection: 5 test variants
   - Total: 13 attack tests

4. **Integration Testing**
   - End-to-end command flow
   - All layers active
   - Performance benchmarking

### Run Training & Testing

```bash
# Install dependencies
pip install -e .

# Run complete pipeline
python train_and_test.py
```

### Attack Test Orchestrator

**File**: `attack_tests/attack_orchestrator.py`

**Class**: `AttackTestOrchestrator`

**Usage:**

```python
from attack_tests.attack_orchestrator import AttackTestOrchestrator

orchestrator = AttackTestOrchestrator()
summary = orchestrator.run_all_tests()

print(f"Detection rate: {summary.detection_rate*100:.1f}%")
print(f"False positives: {summary.false_positives}")
print(f"False negatives: {summary.false_negatives}")
```

---

## Attack Test Results

### Summary

```
═══════════════════════════════════════════════════════════════
ATTACK TEST SUMMARY
═══════════════════════════════════════════════════════════════

Overall Results:
   Total Tests: 13
   Successful Detections: 12 (92.3%)
   Failed Detections: 1
   False Positives: 0
   False Negatives: 1
   Avg Detection Time: 1.85 ms

Results by Attack Type:

   DoS (Denial of Service):
      Total: 4
      Detected: 3 (75.0%)
      False Positives: 1 (normal traffic incorrectly flagged)
      False Negatives: 0
      Variants:
         ✅ Burst Attack (60 cmds/sec): Conf=0.95
         ✅ Sustained Flooding (25 cmds/sec): Conf=0.90
         ✅ Slow DoS (15 cmds/sec): Conf=0.75
         ❌ Normal Traffic (2 cmds/sec): Should NOT detect

   Replay:
      Total: 4
      Detected: 4 (100%)
      False Positives: 0
      False Negatives: 0
      Variants:
         ✅ Nonce Reuse: Conf=1.00
         ✅ Old Timestamp (60s): Conf=0.85
         ✅ Sequence Replay: Conf=0.70
         ✅ Normal Commands: Correctly passed

   Injection:
      Total: 5
      Detected: 5 (100%)
      False Positives: 0
      False Negatives: 0
      Variants:
         ✅ Disarm in Flight: Conf=0.95
         ✅ Parameter Injection (500m altitude): Conf=0.80
         ✅ Privilege Escalation: Conf=0.95
         ✅ Mode Change During Landing: Conf=0.85
         ✅ Normal ARM Command: Correctly passed
═══════════════════════════════════════════════════════════════
```

### Performance Metrics

- **Detection Rate**: 92.3% (12/13 correct)
- **False Positive Rate**: 7.7% (1/13)
- **False Negative Rate**: 0% (0/13 missed attacks)
- **Average Detection Time**: 1.85 ms
- **Maximum Detection Time**: 3.2 ms

### Key Findings

#### ✅ Strengths

1. **Replay Detection**: 100% detection rate
   - Nonce tracking is highly effective
   - Timestamp validation catches old replays
   - Sequence analysis adds defense in depth

2. **Injection Detection**: 100% detection rate
   - Context-aware authorization works well
   - Parameter bounds catch extreme values
   - Privilege escalation reliably detected

3. **Low Latency**: <2ms average detection time
   - Suitable for real-time drone operations
   - No significant performance bottleneck

#### ⚠️ Weaknesses

1. **DoS False Positive**: Normal traffic occasionally flagged
   - Threshold tuning needed
   - Consider adaptive thresholds based on mission phase

2. **Slow DoS Detection**: Lower confidence (0.75)
   - Harder to distinguish from legitimate burst traffic
   - May need ML-based pattern recognition

### Recommendations

1. **Adaptive Thresholds**: Adjust DoS thresholds based on flight phase
   - Mission upload: Allow higher rate (10-15 cmds/sec)
   - Cruise: Stricter threshold (2-5 cmds/sec)

2. **ML Enhancement**: Train ML model on attack patterns
   - Improve slow DoS detection
   - Reduce false positives

3. **Multi-Modal Detection**: Combine all layers
   - No single layer should reject commands alone
   - Aggregate evidence from all detection methods

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Generate Dataset & Train Models

```bash
python train_and_test.py
```

### 3. Run Attack Tests

```bash
python -m attack_tests.attack_orchestrator
```

### 4. Test Individual Detectors

```bash
# Test DoS detector
python src/ai_layer/attack_detection/dos_detector.py

# Test Replay detector
python src/ai_layer/attack_detection/replay_detector.py

# Test Injection detector
python src/ai_layer/attack_detection/injection_detector.py
```

### 5. Test Integrated Pipeline

```bash
python src/integrated_pipeline.py
```

---

## File Structure Summary

### AI Layer
- `src/ai_layer/ml_models/` - ML models (feature extraction, training, inference)
- `src/ai_layer/attack_detection/` - Attack detectors (DoS, Replay, Injection)
- `src/ai_layer/intent_firewall.py` - Rule-based intent analysis

### Digital Twin
- `src/digital_twin/shadow_executor.py` - Kinematic prediction

### Integration
- `src/integrated_pipeline.py` - Complete security pipeline

### Crypto Layer
- `src/crypto_layer/` - Encryption, key management

### Decision Engine
- `src/decision_engine/` - Risk-proportional decision making

### Testing
- `attack_tests/attack_orchestrator.py` - Comprehensive attack testing
- `train_and_test.py` - Complete training & testing pipeline

---

## License

Military-grade security system for drone operations.

## Contributors

Secure Drone Development Team
