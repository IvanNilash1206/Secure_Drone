"""
Model Evaluation and Testing Suite

Evaluates intent inference model on:
1. Per-class precision, recall, F1
2. False positive rate (critical metric!)
3. Inference latency
4. Explainability completeness
5. Attack detection capability
6. Edge case handling

Reports comprehensive metrics for production readiness
"""

import numpy as np
import pandas as pd
import time
import json
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
    precision_score,
    recall_score
)

from src.ai_layer.feature_extractor_v2 import FeatureExtractorV2, CommandContext
from src.ai_layer.inference_v2 import IntentInferenceEngine
from src.ai_layer.intent_labels import IntentClass


class ModelEvaluator:
    """
    Comprehensive model evaluation suite
    
    Metrics:
    - Classification: precision, recall, F1 per class
    - False positive rate (FPR) - CRITICAL
    - Latency: min, max, mean, p95, p99
    - Explainability: feature contribution completeness
    - Attack detection: true positive rate on attack samples
    """
    
    def __init__(self, 
                 model_dir: str = "models/intent_model",
                 test_data_path: str = "data/intent_model/test.csv"):
        self.model_dir = Path(model_dir)
        self.test_data_path = Path(test_data_path)
        
        # Load test data
        self.test_df = pd.read_csv(self.test_data_path)
        
        # Initialize inference engine
        self.engine = IntentInferenceEngine(
            model_dir=str(self.model_dir),
            confidence_threshold=0.6,
            enable_shap=True
        )
        
        # Results storage
        self.predictions = []
        self.latencies = []
        self.explainability_scores = []
        
        print(f"✅ ModelEvaluator initialized")
        print(f"   Test samples: {len(self.test_df)}")
    
    def evaluate_all(self) -> Dict[str, Any]:
        """
        Run complete evaluation suite
        
        Returns comprehensive metrics dict
        """
        print("\n" + "="*70)
        print("🧪 RUNNING MODEL EVALUATION SUITE")
        print("="*70)
        
        # 1. Classification metrics
        print("\n1️⃣  Evaluating classification performance...")
        classification_metrics = self._evaluate_classification()
        
        # 2. False positive rate (CRITICAL!)
        print("\n2️⃣  Computing false positive rate...")
        fpr_metrics = self._evaluate_false_positive_rate()
        
        # 3. Latency benchmarks
        print("\n3️⃣  Benchmarking inference latency...")
        latency_metrics = self._evaluate_latency()
        
        # 4. Explainability
        print("\n4️⃣  Checking explainability completeness...")
        explainability_metrics = self._evaluate_explainability()
        
        # 5. Attack detection
        print("\n5️⃣  Testing attack detection capability...")
        attack_metrics = self._evaluate_attack_detection()
        
        # 6. Edge cases
        print("\n6️⃣  Testing edge case handling...")
        edge_case_metrics = self._evaluate_edge_cases()
        
        # Aggregate all metrics
        full_report = {
            'classification': classification_metrics,
            'false_positive_rate': fpr_metrics,
            'latency': latency_metrics,
            'explainability': explainability_metrics,
            'attack_detection': attack_metrics,
            'edge_cases': edge_case_metrics,
            'overall_status': self._determine_production_readiness(
                classification_metrics,
                fpr_metrics,
                latency_metrics,
                explainability_metrics
            ),
            'evaluation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Save report
        self._save_report(full_report)
        
        # Print summary
        self._print_summary(full_report)
        
        return full_report
    
    def _evaluate_classification(self) -> Dict[str, Any]:
        """Evaluate intent classification performance"""
        
        feature_cols = [c for c in self.test_df.columns if c.startswith('feature_')]
        X_test = self.test_df[feature_cols].values
        y_true = self.test_df['intent_index'].values
        
        y_pred = []
        confidences = []
        
        print(f"   Running inference on {len(X_test)} test samples...")
        
        for i, features in enumerate(X_test):
            result = self.engine.infer(features)
            
            # Convert intent to index
            pred_intent = IntentClass.from_string(result.intent)
            pred_idx = IntentClass.to_index(pred_intent)
            
            y_pred.append(pred_idx)
            confidences.append(result.confidence)
            self.predictions.append(result)
            
            if (i + 1) % 100 == 0:
                print(f"      Progress: {i+1}/{len(X_test)}")
        
        y_pred = np.array(y_pred)
        confidences = np.array(confidences)
        
        # Compute metrics
        intent_names = [IntentClass.from_index(i).value for i in range(9)]
        
        # Per-class metrics
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true, y_pred, labels=range(9), zero_division=0
        )
        
        # Overall metrics
        precision_macro = precision_score(y_true, y_pred, average='macro', zero_division=0)
        recall_macro = recall_score(y_true, y_pred, average='macro', zero_division=0)
        precision_weighted = precision_score(y_true, y_pred, average='weighted', zero_division=0)
        recall_weighted = recall_score(y_true, y_pred, average='weighted', zero_division=0)
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        
        print(f"\n   Overall Precision (weighted): {precision_weighted:.3f}")
        print(f"   Overall Recall (weighted): {recall_weighted:.3f}")
        print(f"   Mean Confidence: {np.mean(confidences):.3f}")
        
        return {
            'precision_per_class': {intent_names[i]: float(precision[i]) for i in range(9)},
            'recall_per_class': {intent_names[i]: float(recall[i]) for i in range(9)},
            'f1_per_class': {intent_names[i]: float(f1[i]) for i in range(9)},
            'support_per_class': {intent_names[i]: int(support[i]) for i in range(9)},
            'precision_macro': float(precision_macro),
            'recall_macro': float(recall_macro),
            'precision_weighted': float(precision_weighted),
            'recall_weighted': float(recall_weighted),
            'mean_confidence': float(np.mean(confidences)),
            'confusion_matrix': cm.tolist(),
        }
    
    def _evaluate_false_positive_rate(self) -> Dict[str, Any]:
        """
        False positive rate: Benign commands flagged as high-risk
        
        This is CRITICAL - we want low FPR to avoid blocking legitimate commands
        """
        # Filter to non-attack samples
        normal_samples = self.test_df[self.test_df['is_attack'] == False]
        
        false_positives = 0
        total_normal = len(normal_samples)
        
        for idx, row in normal_samples.iterrows():
            # Get prediction for this sample
            pred_idx = normal_samples.index.get_loc(idx)
            if pred_idx < len(self.predictions):
                result = self.predictions[pred_idx]
                
                # False positive: Normal command with high risk score
                if result.intent_risk > 0.7 and result.confidence > 0.6:
                    false_positives += 1
        
        fpr = false_positives / max(1, total_normal)
        
        print(f"   False Positives: {false_positives}/{total_normal}")
        print(f"   FPR: {fpr:.3%}")
        
        # Target: FPR < 5%
        meets_target = fpr < 0.05
        
        return {
            'false_positives': false_positives,
            'total_normal_samples': total_normal,
            'fpr': float(fpr),
            'meets_5pct_target': meets_target,
        }
    
    def _evaluate_latency(self) -> Dict[str, Any]:
        """Benchmark inference latency"""
        
        # Extract latencies from predictions
        latencies = [p.inference_time_ms for p in self.predictions]
        
        if not latencies:
            return {'error': 'No latency data'}
        
        latencies_np = np.array(latencies)
        
        min_latency = np.min(latencies_np)
        max_latency = np.max(latencies_np)
        mean_latency = np.mean(latencies_np)
        median_latency = np.median(latencies_np)
        p95_latency = np.percentile(latencies_np, 95)
        p99_latency = np.percentile(latencies_np, 99)
        
        # Target: <10ms
        meets_target = p95_latency < 10.0
        
        print(f"   Mean: {mean_latency:.2f}ms")
        print(f"   Median: {median_latency:.2f}ms")
        print(f"   P95: {p95_latency:.2f}ms")
        print(f"   P99: {p99_latency:.2f}ms")
        print(f"   Min: {min_latency:.2f}ms, Max: {max_latency:.2f}ms")
        
        return {
            'min_ms': float(min_latency),
            'max_ms': float(max_latency),
            'mean_ms': float(mean_latency),
            'median_ms': float(median_latency),
            'p95_ms': float(p95_latency),
            'p99_ms': float(p99_latency),
            'meets_10ms_target': meets_target,
        }
    
    def _evaluate_explainability(self) -> Dict[str, Any]:
        """Check explainability completeness"""
        
        complete_explanations = 0
        partial_explanations = 0
        no_explanations = 0
        
        for pred in self.predictions:
            if len(pred.top_features) >= 3 and len(pred.feature_contributions) >= 3:
                complete_explanations += 1
            elif len(pred.top_features) > 0:
                partial_explanations += 1
            else:
                no_explanations += 1
        
        total = len(self.predictions)
        completeness_rate = complete_explanations / max(1, total)
        
        print(f"   Complete explanations: {complete_explanations}/{total} ({completeness_rate:.1%})")
        
        return {
            'complete_explanations': complete_explanations,
            'partial_explanations': partial_explanations,
            'no_explanations': no_explanations,
            'total_predictions': total,
            'completeness_rate': float(completeness_rate),
            'meets_80pct_target': completeness_rate >= 0.8,
        }
    
    def _evaluate_attack_detection(self) -> Dict[str, Any]:
        """Test attack detection capability"""
        
        # Filter to attack samples
        attack_samples = self.test_df[self.test_df['is_attack'] == True]
        
        if len(attack_samples) == 0:
            return {'error': 'No attack samples in test set'}
        
        detected = 0
        total_attacks = len(attack_samples)
        
        for idx, row in attack_samples.iterrows():
            pred_idx = attack_samples.index.get_loc(idx)
            if pred_idx < len(self.predictions):
                result = self.predictions[pred_idx]
                
                # Attack detected if high risk + high confidence
                if result.intent_risk > 0.6 and result.confidence > 0.6:
                    detected += 1
        
        detection_rate = detected / max(1, total_attacks)
        
        print(f"   Attacks detected: {detected}/{total_attacks} ({detection_rate:.1%})")
        
        return {
            'attacks_detected': detected,
            'total_attacks': total_attacks,
            'detection_rate': float(detection_rate),
            'meets_80pct_target': detection_rate >= 0.8,
        }
    
    def _evaluate_edge_cases(self) -> Dict[str, Any]:
        """Test edge case handling"""
        
        # Test with invalid inputs
        test_cases = {
            'null_input': None,
            'wrong_dimension': np.random.rand(10),  # Wrong size
            'all_zeros': np.zeros(37),
            'all_ones': np.ones(37),
            'extreme_values': np.random.rand(37) * 1000,
        }
        
        results = {}
        
        for case_name, input_vec in test_cases.items():
            try:
                result = self.engine.infer(input_vec)
                
                # Check if gracefully handled
                if result.model_status == "FALLBACK":
                    results[case_name] = "PASS: Graceful fallback"
                elif result.confidence > 0:
                    results[case_name] = f"PASS: Prediction (conf={result.confidence:.2f})"
                else:
                    results[case_name] = "WARN: Zero confidence"
                    
            except Exception as e:
                results[case_name] = f"FAIL: Exception - {str(e)}"
        
        # Count passes
        passes = sum(1 for v in results.values() if 'PASS' in v)
        
        print(f"   Edge cases passed: {passes}/{len(test_cases)}")
        
        return {
            'test_cases': results,
            'passes': passes,
            'total': len(test_cases),
            'all_passed': passes == len(test_cases),
        }
    
    def _determine_production_readiness(self,
                                       classification_metrics,
                                       fpr_metrics,
                                       latency_metrics,
                                       explainability_metrics) -> Dict[str, Any]:
        """Determine if model is production-ready"""
        
        criteria = {
            'precision_sufficient': classification_metrics['precision_weighted'] >= 0.75,
            'fpr_acceptable': fpr_metrics.get('meets_5pct_target', False),
            'latency_acceptable': latency_metrics.get('meets_10ms_target', False),
            'explainability_sufficient': explainability_metrics.get('meets_80pct_target', False),
        }
        
        all_pass = all(criteria.values())
        
        return {
            'production_ready': all_pass,
            'criteria_met': criteria,
            'blockers': [k for k, v in criteria.items() if not v],
        }
    
    def _save_report(self, report: Dict[str, Any]):
        """Save evaluation report to disk"""
        output_path = self.model_dir / 'evaluation_report.json'
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Evaluation report saved: {output_path}")
    
    def _print_summary(self, report: Dict[str, Any]):
        """Print evaluation summary"""
        
        print("\n" + "="*70)
        print("📊 EVALUATION SUMMARY")
        print("="*70)
        
        print("\n✅ Classification:")
        print(f"   Precision: {report['classification']['precision_weighted']:.3f}")
        print(f"   Recall: {report['classification']['recall_weighted']:.3f}")
        
        print("\n🎯 False Positive Rate:")
        print(f"   FPR: {report['false_positive_rate']['fpr']:.3%}")
        status = "✅ PASS" if report['false_positive_rate']['meets_5pct_target'] else "❌ FAIL"
        print(f"   Target (<5%): {status}")
        
        print("\n⚡ Latency:")
        print(f"   P95: {report['latency']['p95_ms']:.2f}ms")
        status = "✅ PASS" if report['latency']['meets_10ms_target'] else "❌ FAIL"
        print(f"   Target (<10ms): {status}")
        
        print("\n🔍 Explainability:")
        print(f"   Completeness: {report['explainability']['completeness_rate']:.1%}")
        status = "✅ PASS" if report['explainability']['meets_80pct_target'] else "❌ FAIL"
        print(f"   Target (>80%): {status}")
        
        print("\n🛡️  Attack Detection:")
        print(f"   Detection Rate: {report['attack_detection']['detection_rate']:.1%}")
        
        print("\n🚀 PRODUCTION READINESS:")
        if report['overall_status']['production_ready']:
            print("   ✅ MODEL IS PRODUCTION READY")
        else:
            print("   ❌ NOT READY - Blockers:")
            for blocker in report['overall_status']['blockers']:
                print(f"      - {blocker}")
        
        print("\n" + "="*70)


if __name__ == "__main__":
    # Run full evaluation
    evaluator = ModelEvaluator(
        model_dir="models/intent_model",
        test_data_path="data/intent_model/test.csv"
    )
    
    report = evaluator.evaluate_all()
    
    print("\n✅ Evaluation complete!")
    print(f"\nFull report saved to: models/intent_model/evaluation_report.json")
