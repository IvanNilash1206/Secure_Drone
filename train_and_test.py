"""
Complete Training and Testing Pipeline

Orchestrates:
1. Dataset generation (normal + attack scenarios)
2. ML model training (intent classifier + risk regressor)
3. Model evaluation
4. Attack testing
5. Integration testing

Run this script to train and validate the complete system.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

print("="*80)
print("SECURE DRONE - ML TRAINING & TESTING PIPELINE")
print("="*80)

# Step 1: Generate training dataset
print("\n📊 STEP 1: Generating Training Dataset...")
print("-"*80)

try:
    from src.ai_layer.ml_models.dataset_generator import DatasetGenerator
    
    dataset_dir = Path("datasets")
    dataset_dir.mkdir(exist_ok=True)
    
    generator = DatasetGenerator(output_dir=str(dataset_dir))
    
    # Generate scenarios: 100 normal, 50 of each attack type
    train_df, val_df, test_df = generator.generate_full_dataset(
        n_normal=100,
        n_attacks=50,
        train_ratio=0.7,
        val_ratio=0.15
    )
    
    print(f"\n✅ Dataset generated:")
    print(f"   Training samples: {len(train_df)}")
    print(f"   Validation samples: {len(val_df)}")
    print(f"   Test samples: {len(test_df)}")
    
    dataset_generated = True
    
except Exception as e:
    print(f"\n❌ Dataset generation failed: {e}")
    print("   Continuing with existing dataset if available...")
    dataset_generated = False


# Step 2: Train ML models
print("\n\n🤖 STEP 2: Training ML Models...")
print("-"*80)

try:
    from src.ai_layer.ml_models.trainer import IntentModelTrainer
    import pandas as pd
    
    # Load dataset if not generated
    if not dataset_generated:
        dataset_dir = Path("datasets")
        train_df = pd.read_csv(dataset_dir / "train_dataset.csv")
        val_df = pd.read_csv(dataset_dir / "val_dataset.csv")
        test_df = pd.read_csv(dataset_dir / "test_dataset.csv")
    
    # Train models
    model_dir = Path("models/intent_model")
    trainer = IntentModelTrainer(model_dir=str(model_dir))
    
    metrics = trainer.train(
        train_df=train_df,
        val_df=val_df,
        optimize_for='inference_speed'
    )
    
    print(f"\n✅ Models trained:")
    print(f"   Intent Classifier Accuracy: {metrics['classifier']['accuracy']:.3f}")
    print(f"   Risk Regressor MAE: {metrics['regressor']['mae']:.3f}")
    print(f"   Models saved to: {model_dir}")
    
    # Test inference speed
    from src.ai_layer.ml_models.inference import IntentInferenceEngine
    
    engine = IntentInferenceEngine(model_dir=str(model_dir))
    
    # Dummy feature vector for speed test
    import numpy as np
    dummy_features = np.zeros(37)
    
    # Warm-up
    for _ in range(10):
        engine.predict(dummy_features)
    
    # Speed test
    start = time.time()
    for _ in range(100):
        engine.predict(dummy_features)
    avg_time = (time.time() - start) / 100 * 1000
    
    print(f"   Average inference time: {avg_time:.2f} ms")
    
    models_trained = True
    
except Exception as e:
    print(f"\n❌ Model training failed: {e}")
    import traceback
    traceback.print_exc()
    models_trained = False


# Step 3: Run attack tests
print("\n\n🛡️ STEP 3: Running Attack Detection Tests...")
print("-"*80)

try:
    from attack_tests.attack_orchestrator import AttackTestOrchestrator
    
    orchestrator = AttackTestOrchestrator()
    summary = orchestrator.run_all_tests()
    
    print(f"\n✅ Attack testing complete:")
    print(f"   Detection rate: {summary.detection_rate*100:.1f}%")
    print(f"   False positives: {summary.false_positives}")
    print(f"   False negatives: {summary.false_negatives}")
    
    attack_tests_passed = summary.detection_rate >= 0.80  # 80% threshold
    
except Exception as e:
    print(f"\n❌ Attack testing failed: {e}")
    import traceback
    traceback.print_exc()
    attack_tests_passed = False


# Step 4: Integration test
print("\n\n🔗 STEP 4: Integration Test...")
print("-"*80)

try:
    from src.crypto_layer.crypto_gate import CryptoGate
    from src.crypto_layer.encryptor import encrypt_payload
    from src.decision_engine.decision_engine import RiskProportionalDecisionEngine
    from src.digital_twin.shadow_executor import ShadowExecutor
    from src.ai_layer.intent_firewall import IntentFirewall
    
    # Initialize all layers
    crypto_gate = CryptoGate()
    intent_firewall = IntentFirewall()
    shadow_executor = ShadowExecutor()
    decision_engine = RiskProportionalDecisionEngine()
    
    # Simulate command flow
    print("\nSimulating command: ARM_AND_TAKEOFF")
    
    # 1. Encrypt command
    payload = b"ARM_AND_TAKEOFF|" + str(time.time()).encode() + b"|GCS"
    nonce, ciphertext = encrypt_payload(payload)
    print("   ✓ Command encrypted")
    
    # 2. Crypto validation
    crypto_valid, decrypted_payload = crypto_gate.crypto_check(nonce, ciphertext)
    if crypto_valid:
        print(f"   ✓ Crypto validation passed")
    else:
        print("   ✗ Crypto validation failed")
        raise ValueError("Crypto check failed")
    
    # 3. Intent analysis
    intent_result = intent_firewall.analyze_command("ARM_AND_TAKEOFF")
    print(f"   ✓ Intent: {intent_result.intent.value}, Match: {intent_result.intent_match}")
    
    # 4. Shadow execution
    shadow_result = shadow_executor.predict_outcome("ARM_AND_TAKEOFF", {})
    print(f"   ✓ Shadow risk: {shadow_result.trajectory_risk:.2f}")
    
    # 5. Decision engine
    decision_result = decision_engine.decide(
        command="ARM_AND_TAKEOFF",
        crypto_valid=crypto_valid,
        intent_result=intent_result,
        ml_inference=None,  # Would use ML model here
        shadow_result=shadow_result
    )
    print(f"   ✓ Decision: {decision_result.decision.value}, Severity: {decision_result.severity.value}")
    
    print("\n✅ Integration test passed!")
    integration_passed = True
    
except Exception as e:
    print(f"\n❌ Integration test failed: {e}")
    import traceback
    traceback.print_exc()
    integration_passed = False


# Final Summary
print("\n\n" + "="*80)
print("PIPELINE SUMMARY")
print("="*80)

results = {
    "Dataset Generation": "✅ PASS" if dataset_generated else "⚠️ SKIP",
    "Model Training": "✅ PASS" if models_trained else "❌ FAIL",
    "Attack Testing": "✅ PASS" if attack_tests_passed else "❌ FAIL",
    "Integration Test": "✅ PASS" if integration_passed else "❌ FAIL"
}

for step, status in results.items():
    print(f"{step:.<50} {status}")

all_passed = models_trained and attack_tests_passed and integration_passed

print("\n" + "="*80)
if all_passed:
    print("✅ ALL TESTS PASSED - System ready for deployment!")
else:
    print("⚠️ Some tests failed - Review logs above")
print("="*80)
