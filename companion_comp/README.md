# 🟩 Companion Computer (AEGIS) Component

## What This Component Represents

This represents the **security gateway and decision enforcer** - the trusted guardian sitting between operators/attackers and the flight controller.

## Real-World UAV System Role

**Location**: Companion computer (Raspberry Pi, NVIDIA Jetson, etc.) mounted on the drone  
**Network Access**: Receives traffic from GCS/network, forwards to flight controller  
**Trust Level**: **HIGHEST TRUST** - Only component allowed to talk to flight controller  

## Responsibilities

### What AEGIS DOES:
- ✅ Acts as ONLY gateway to flight controller (mandatory checkpoint)
- ✅ Enforces cryptographic validation (message authentication)
- ✅ Performs AI-based threat detection (intent classification, anomaly detection)
- ✅ Executes shadow execution (trajectory prediction, physics constraints)
- ✅ Makes risk-based decisions (allow/block/modify)
- ✅ Generates explainable audit logs
- ✅ Protects against GPS spoofing, waypoint injection, command injection, DoS

### What AEGIS DOES NOT DO:
- ❌ Does not assume trust
- ❌ Does not modify ArduPilot firmware
- ❌ Does not rely on obscurity

## Architecture Position

```
┌────────────────────────────────────────────────────────┐
│                    NETWORK LAYER                       │
│                                                        │
│  ┌──────────────┐                                     │
│  │   ATTACKER   │  ──────────┐                        │
│  │  (Laptop 1)  │             │                        │
│  │  UDP:14560   │             ▼                        │
│  └──────────────┘      ┌──────────────┐               │
│                        │ AEGIS PROXY  │               │
│  ┌──────────────┐      │ (Companion)  │               │
│  │     GCS      │ ───▶ │  UDP:14560   │ ──▶ FC SITL  │
│  │  (Laptop 2)  │      │     ▼        │     UDP:14550│
│  │  UDP:14560   │      │  Security    │               │
│  └──────────────┘      │   Layers     │               │
│                        └──────────────┘               │
└────────────────────────────────────────────────────────┘
```

## Security Layer Architecture

```
┌─────────────────────────────────────────────────┐
│            AEGIS Security Gateway               │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │   1. Intent Firewall                    │   │
│  │      - Intent Classification            │   │
│  │      - Rules Engine                     │   │
│  │      - Feature Extraction               │   │
│  └─────────────────────────────────────────┘   │
│                    ▼                            │
│  ┌─────────────────────────────────────────┐   │
│  │   2. Behavior IDS                       │   │
│  │      - Anomaly Detection                │   │
│  │      - Temporal Modeling                │   │
│  └─────────────────────────────────────────┘   │
│                    ▼                            │
│  ┌─────────────────────────────────────────┐   │
│  │   3. Shadow Execution                   │   │
│  │      - Trajectory Prediction            │   │
│  │      - Physics Constraints              │   │
│  └─────────────────────────────────────────┘   │
│                    ▼                            │
│  ┌─────────────────────────────────────────┐   │
│  │   4. Decision Engine                    │   │
│  │      - Risk Aggregation                 │   │
│  │      - Response Management              │   │
│  └─────────────────────────────────────────┘   │
│                    ▼                            │
│  ┌─────────────────────────────────────────┐   │
│  │   5. Logger                             │   │
│  │      - Audit Logging                    │   │
│  │      - Explainability                   │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Directory Structure

```
companion_comp/
├── aegis_proxy.py                  # Main proxy entry point
├── config.yaml                     # Configuration file
├── requirements.txt                # Python dependencies
│
├── intent_firewall/                # Layer 1: Intent Classification
│   ├── intent_classifier.py        # AI-based intent recognition
│   ├── rules_engine.py             # Policy enforcement rules
│   └── features.py                 # Feature extraction
│
├── behavior_ids/                   # Layer 2: Behavioral Analysis
│   ├── anomaly_detector.py         # Anomaly detection
│   └── temporal_model.py           # Temporal pattern analysis
│
├── shadow_execution/               # Layer 3: Predictive Analysis
│   ├── trajectory_predictor.py     # Flight path prediction
│   └── physics_constraints.py      # Physics validation
│
├── decision_engine/                # Layer 4: Decision Making
│   ├── risk_aggregator.py          # Risk score calculation
│   └── response_manager.py         # Response execution
│
├── logger/                         # Layer 5: Audit & Explainability
│   ├── audit_logger.py             # Audit trail
│   └── explainability.py           # Decision explanations
│
└── crypto_layer/                   # Cryptographic Operations
    ├── encryptor.py
    ├── decryptor.py
    ├── key_manager.py
    └── nonce_manager.py
```

## How to Run

### 1. Basic Startup (All Security Enabled)
```bash
cd companion_comp
python aegis_proxy.py
```

### 2. With Custom Configuration
```bash
python aegis_proxy.py --config config.yaml
```

### 3. Pass-Through Mode (No Security - For Testing)
```bash
python aegis_proxy.py --no-security
```

## Security Layers Explained

### 1. Intent Firewall
**Purpose**: Classify command intent and block malicious intents  
**Techniques**: AI-based classification, rule-based policies  
**Blocks**: GPS spoofing, unauthorized waypoint injection  

### 2. Behavior IDS
**Purpose**: Detect anomalous behavioral patterns  
**Techniques**: Temporal analysis, frequency analysis  
**Blocks**: DoS flooding, unusual command sequences  

### 3. Shadow Execution
**Purpose**: Predict outcome before execution  
**Techniques**: Trajectory prediction, physics simulation  
**Blocks**: Commands that violate physics or safety constraints  

### 4. Decision Engine
**Purpose**: Aggregate risk scores and make final decisions  
**Techniques**: Multi-factor risk scoring, threshold-based blocking  
**Actions**: ALLOW, BLOCK, MODIFY, SAFE_MODE  

### 5. Logger
**Purpose**: Create audit trail and explain decisions  
**Techniques**: Structured logging, explainability generation  
**Outputs**: Audit logs, explainability reports  

## Configuration

Edit `config.yaml` to customize:
- Network ports and interfaces
- Security layer enable/disable
- AI model thresholds
- Risk thresholds
- Logging levels

## Dependencies

```bash
cd companion_comp
pip install -r requirements.txt
```

## Logs

- **aegis_proxy.log**: Main proxy operations
- **aegis_audit.log**: Security audit trail
- **aegis_explainability.log**: Decision explanations

## Why This Component is Separated

1. **Real-world deployment**: Companion computers are physically separate hardware
2. **Security boundary enforcement**: Only this component can reach FC
3. **Defense-in-depth**: Multiple security layers in sequence
4. **Auditability**: Clear audit trail of all decisions
5. **Explainability**: Transparent decision-making process

## Expected Behavior

### Legitimate GCS Traffic:
- ✅ Passes all security layers
- ✅ Forwarded to flight controller
- ✅ Logged as ALLOWED

### Attacker Traffic:
- ❌ Blocked by one or more security layers
- ❌ Never reaches flight controller
- ❌ Logged as BLOCKED with explanation

## Educational Value

For judges evaluating this system:
1. This is the **heart of the security architecture**
2. Demonstrates **defense-in-depth** (multiple layers)
3. Shows **zero-trust** approach (all traffic validated)
4. Provides **explainability** (why was it blocked?)
5. Proves **practical deployability** (runs on real hardware)

## Demo Script for Judges

1. **Start AEGIS proxy** - observe security layers load
2. **Send GCS commands** - observe allowed traffic flow
3. **Send attacker commands** - observe blocked traffic
4. **Review audit logs** - see decision explanations
5. **Compare with/without AEGIS** - see the difference

This is why AEGIS is necessary even with firewall - it analyzes **content**, not just **topology**.
