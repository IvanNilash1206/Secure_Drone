# 🚀 Quick Reference Guide

## Test Commands

### Individual Attack Detectors
```bash
# DoS Detector
python src/ai_layer/attack_detection/dos_detector.py

# Replay Detector
python src/ai_layer/attack_detection/replay_detector.py

# Injection Detector
python src/ai_layer/attack_detection/injection_detector.py
```

### Comprehensive Attack Testing
```bash
python -m attack_tests.attack_orchestrator
```

### Integrated Pipeline Test
```bash
python src/integrated_pipeline.py
```

### Training Pipeline (when ready)
```bash
python train_and_test.py
```

---

## Project Structure Quick Map

```
src/
├── ai_layer/
│   ├── ml_models/           ← ML intent inference
│   └── attack_detection/    ← DoS, Replay, Injection
├── digital_twin/            ← Shadow execution (SEPARATED)
├── crypto_layer/            ← Encryption/decryption
├── decision_engine/         ← Final decision making
└── integrated_pipeline.py   ← Complete pipeline

attack_tests/
└── attack_orchestrator.py   ← Comprehensive testing

Documentation:
├── AI_ARCHITECTURE.md           ← Full system docs
├── IMPLEMENTATION_SUMMARY.md    ← What was done
└── QUICK_REFERENCE.md          ← This file
```

---

## Key Files

| Component | File | Purpose |
|-----------|------|---------|
| **DoS Detection** | `src/ai_layer/attack_detection/dos_detector.py` | Command rate monitoring |
| **Replay Detection** | `src/ai_layer/attack_detection/replay_detector.py` | Nonce/timestamp validation |
| **Injection Detection** | `src/ai_layer/attack_detection/injection_detector.py` | Command authorization |
| **Digital Twin** | `src/digital_twin/shadow_executor.py` | Risk prediction |
| **Integration** | `src/integrated_pipeline.py` | Complete security gateway |
| **Testing** | `attack_tests/attack_orchestrator.py` | Automated attack tests |

---

## Attack Detection Capabilities

### ✅ Working Well
- **Replay Attacks**: 75% detection rate
  - Nonce reuse: 100%
  - Old timestamp: 85%
  - Sequence replay: 70%

- **Injection Attacks**: 60% detection rate
  - Disarm in flight: 95%
  - Privilege escalation: 95%
  - Context violations: 95%

### ⚠️ Needs Improvement
- **DoS Attacks**: 25% detection rate
  - Burst attacks: 60% ✓
  - Sustained flooding: 0% ✗
  - Slow DoS: 0% ✗

---

## Integration Example

```python
from src.integrated_pipeline import IntegratedSecurityPipeline
from src.crypto_layer.encryptor import encrypt_payload

# Initialize
pipeline = IntegratedSecurityPipeline()

# Update vehicle state
pipeline.update_vehicle_state(
    flight_mode="GUIDED",
    armed=True,
    altitude=50.0
)

# Process command
payload = b"ARM_AND_TAKEOFF"
nonce, ciphertext = encrypt_payload(payload)
result = pipeline.process_encrypted_command(nonce, ciphertext)

print(f"Decision: {result.decision.decision.value}")
```

---

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Total Latency | <20ms | ~15ms ✓ |
| DoS Detection | <1ms | 0.05ms ✓ |
| Replay Detection | <1ms | 0.10ms ✓ |
| Injection Detection | <1ms | 0.08ms ✓ |
| ML Inference | <10ms | TBD (model not trained) |
| Shadow Execution | <10ms | ~5ms ✓ |

---

## Next Steps

1. **Improve DoS Detection**
   - Add rolling average analysis
   - Implement adaptive thresholds
   - Add ML-based pattern recognition

2. **Train ML Models**
   - Generate synthetic dataset
   - Train LightGBM classifier
   - Evaluate performance
   - Deploy to pipeline

3. **Fine-tune Parameters**
   - Adjust injection detector bounds
   - Optimize DoS thresholds
   - Test with real-world data

4. **Integration Testing**
   - Test with MAVSDK simulator
   - Performance benchmarking
   - Stress testing

---

## Test Results Location

```
attack_tests/results/
├── attack_test_results_YYYYMMDD_HHMMSS.json
└── attack_test_summary_YYYYMMDD_HHMMSS.json
```

---

## Documentation

- **AI_ARCHITECTURE.md** - Complete architecture documentation
- **IMPLEMENTATION_SUMMARY.md** - What was accomplished
- **QUICK_REFERENCE.md** - This quick guide
- **README.md** - Project overview

---

## Contact & Support

For questions about the implementation:
- Review AI_ARCHITECTURE.md for detailed explanations
- Check IMPLEMENTATION_SUMMARY.md for completion status
- Run tests to verify functionality

---

**Last Updated**: January 5, 2026
