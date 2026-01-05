# Layer Separation Diagram

## Before Restructuring

```
src/ai_layer/
├── shadow_executor.py          ← Digital Twin (mixed in)
├── intent_firewall.py
├── feature_extractor_v2.py     ← ML component
├── inference_v2.py             ← ML component
├── train_model_v2.py           ← ML component
├── dataset_generator.py        ← ML component
├── mode_aware_ids.py           ← Attack detection (unclear)
├── trust_model.py
├── normalizer.py
└── ... (many other files)
```

**Problem**: Everything mixed together, unclear boundaries

---

## After Restructuring ✅

```
src/
├── ai_layer/
│   ├── ml_models/                    ← ML Intent Inference (GROUPED)
│   │   ├── __init__.py
│   │   ├── feature_extractor.py     (was feature_extractor_v2.py)
│   │   ├── inference.py             (was inference_v2.py)
│   │   ├── trainer.py               (was train_model_v2.py)
│   │   └── dataset_generator.py
│   │
│   ├── attack_detection/             ← Attack Detection (NEW)
│   │   ├── __init__.py
│   │   ├── dos_detector.py          (NEW)
│   │   ├── replay_detector.py       (NEW)
│   │   ├── injection_detector.py    (NEW)
│   │   └── anomaly_detector.py      (was mode_aware_ids.py)
│   │
│   ├── intent_firewall.py           ← Core AI (rule-based)
│   ├── intent_labels.py
│   ├── trust_model.py
│   └── normalizer.py
│
├── digital_twin/                     ← Digital Twin (SEPARATED)
│   ├── __init__.py
│   └── shadow_executor.py           (MOVED from ai_layer/)
│
├── crypto_layer/                     ← Crypto (unchanged)
│   └── ...
│
├── decision_engine/                  ← Decision (unchanged)
│   └── ...
│
└── integrated_pipeline.py           ← Integration (NEW)
```

---

## Layer Responsibilities

### 1. AI Layer (`src/ai_layer/`)

#### ML Models (`ml_models/`)
**Purpose**: Intent inference using machine learning

**Components**:
- Feature extraction (37 features)
- LightGBM classifier (9 intent classes)
- Risk regressor
- Training & dataset generation

**Input**: Command + context
**Output**: Intent class + confidence + risk score

#### Attack Detection (`attack_detection/`)
**Purpose**: Real-time attack detection

**Components**:
- DoS detector (rate monitoring)
- Replay detector (nonce/timestamp/sequence)
- Injection detector (authorization/parameters/context)

**Input**: Command metadata
**Output**: Attack detected (yes/no) + confidence

#### Core AI
**Purpose**: Rule-based intent analysis

**Components**:
- Intent firewall
- Trust scoring
- Command history

---

### 2. Digital Twin Layer (`src/digital_twin/`)

**Purpose**: Kinematic prediction & risk assessment

**NOT full simulation** - just lightweight prediction

**Predictions**:
- Geofence violations
- Altitude/velocity risk
- Energy margin
- Loss-of-control risk

**Input**: Command + vehicle state
**Output**: Predicted outcomes + trajectory risk

**Key Difference from AI Layer**:
- AI Layer = What is the intent? Is it malicious?
- Digital Twin = What will happen if we execute?

---

### 3. Crypto Layer (`src/crypto_layer/`)

**Purpose**: Encryption, decryption, key management

**Components**:
- AES-256-GCM encryption
- Hierarchical key management
- Nonce management

---

### 4. Decision Engine (`src/decision_engine/`)

**Purpose**: Aggregate all layer outputs → final decision

**Input**: All layer results
**Output**: ACCEPT / REJECT / CONSTRAIN / RTL

---

## Data Flow

```
Encrypted Command
    ↓
┌─────────────────────────────────┐
│  CRYPTO LAYER                   │
│  Decrypt & Validate             │
└────────────┬────────────────────┘
             ↓
     ┌───────┴────────┐
     │                │
┌────▼────────┐  ┌───▼────────────┐
│  AI LAYER   │  │ ATTACK DETECT  │
│  Intent?    │  │ Malicious?     │
└────┬────────┘  └───┬────────────┘
     │               │
     └───────┬───────┘
             ↓
┌────────────▼────────────────────┐
│  DIGITAL TWIN                   │
│  What will happen?              │
└────────────┬────────────────────┘
             ↓
┌────────────▼────────────────────┐
│  DECISION ENGINE                │
│  ACCEPT / REJECT / RTL          │
└─────────────────────────────────┘
```

---

## Key Separation Principles

### AI Layer vs Digital Twin

| Aspect | AI Layer | Digital Twin |
|--------|----------|--------------|
| **Question** | "What is this command?" | "What will happen?" |
| **Method** | Pattern recognition, ML | Physics, kinematics |
| **Input** | Command + history | Command + vehicle state |
| **Output** | Intent + maliciousness | Risk + outcomes |
| **Time Horizon** | Current command | 5-10 seconds ahead |
| **Certainty** | Probabilistic | Deterministic |

### Why Separate?

1. **Different concerns**:
   - AI = Understanding intent
   - Digital Twin = Predicting outcomes

2. **Different expertise**:
   - AI = ML engineers, security experts
   - Digital Twin = Control engineers, physicists

3. **Different testing**:
   - AI = Dataset, accuracy, confusion matrix
   - Digital Twin = Simulation, prediction accuracy

4. **Different evolution**:
   - AI = More data → better models
   - Digital Twin = Better physics → better predictions

---

## Integration Points

### How Layers Communicate

```python
# In integrated_pipeline.py

class IntegratedSecurityPipeline:
    def __init__(self):
        # Initialize all layers
        self.crypto_gate = CryptoGate()
        self.dos_detector = DoSDetector()
        self.replay_detector = ReplayDetector()
        self.injection_detector = InjectionDetector()
        self.intent_firewall = IntentFirewall()
        self.ml_engine = IntentInferenceEngine()
        self.shadow_executor = ShadowExecutor()    # Digital Twin
        self.decision_engine = RiskProportionalDecisionEngine()
    
    def process_command(self, nonce, ciphertext):
        # 1. Crypto
        crypto_valid, payload = self.crypto_gate.crypto_check(...)
        
        # 2. Attack Detection
        dos_metrics = self.dos_detector.record_command(...)
        replay_metrics = self.replay_detector.check_command(...)
        injection_metrics = self.injection_detector.check_command(...)
        
        # 3. AI Intent Analysis
        intent_result = self.intent_firewall.analyze_command(...)
        ml_inference = self.ml_engine.predict(...)
        
        # 4. Digital Twin
        shadow_result = self.shadow_executor.predict_outcome(...)
        
        # 5. Decision
        decision = self.decision_engine.decide(
            crypto_valid=crypto_valid,
            dos_metrics=dos_metrics,
            replay_metrics=replay_metrics,
            injection_metrics=injection_metrics,
            intent_result=intent_result,
            ml_inference=ml_inference,
            shadow_result=shadow_result    # Digital Twin input
        )
        
        return decision
```

---

## Summary

### What Changed

1. **AI Layer** split into:
   - `ml_models/` - ML intent inference
   - `attack_detection/` - Real-time attack detection
   - Core AI files (intent_firewall, etc.)

2. **Digital Twin** separated:
   - Moved to `src/digital_twin/`
   - Clear interface with decision engine
   - Focus on prediction, not intent

3. **Integration** centralized:
   - `integrated_pipeline.py` - Single entry point
   - All layers coordinated
   - Clear data flow

### Benefits

✅ **Clarity**: Each layer has clear purpose
✅ **Maintainability**: Easy to modify individual layers
✅ **Testability**: Can test each layer independently
✅ **Extensibility**: Easy to add new detectors or predictors
✅ **Performance**: Can optimize each layer separately

---

**Visual Reference Complete** ✓
