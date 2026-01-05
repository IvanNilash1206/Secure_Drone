"""
Layer 7: Explainable Action + Audit Logger (NOVEL COMPONENT 🧾)

Purpose: Make system accountable and defensible

For every decision:
1. Human-readable explanation
2. Machine-readable audit log (immutable JSONL)
3. Post-flight analysis ready
4. Regulator-friendly format
"""

import json
import time
from typing import Dict, Any
from pathlib import Path
from datetime import datetime


class ExplainableLogger:
    """
    Generates explanations and maintains audit trail
    
    Output Format:
    - Human: Plain English explanation of WHY decision was made
    - Machine: Structured JSONL for analysis
    - Immutable: Append-only log
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Separate log files
        self.decision_log = self.log_dir / "decision_log.jsonl"
        self.audit_log = self.log_dir / "audit_trail.jsonl"
        self.human_log = self.log_dir / "decisions_explained.txt"
        
        # Session metadata
        self.session_id = f"session_{int(time.time())}"
        self.command_counter = 0
        
        print(f"✅ Explainable Logger initialized: {self.log_dir}")
        self._write_session_header()
    
    def _write_session_header(self):
        """Write session start marker"""
        header = f"\n{'='*80}\n"
        header += f"AEGIS Decision Log - Session {self.session_id}\n"
        header += f"Started: {datetime.now().isoformat()}\n"
        header += f"{'='*80}\n\n"
        
        with open(self.human_log, "a") as f:
            f.write(header)
    
    def generate_human_explanation(self, 
                                   command_obj,
                                   decision_result,
                                   intent_result,
                                   behavior_result,
                                   shadow_result,
                                   crypto_valid: bool) -> str:
        """
        Generate plain English explanation
        
        Example:
        "Command rejected because predicted trajectory exits geofence 
        in 6.2 seconds during AUTO mission."
        """
        decision = decision_result.decision.value
        severity = decision_result.severity.value
        
        # Start with decision
        explanation = f"Decision: {decision} (Severity: {severity})\n"
        explanation += f"Command: {command_obj.command_type} from {command_obj.source}\n"
        explanation += f"Risk Score: {decision_result.contributing_factors['risk_score']}\n\n"
        
        # Reasoning chain
        explanation += "Reasoning:\n"
        
        # Layer 2: Crypto
        if crypto_valid:
            explanation += "✓ Cryptographic validation: PASSED\n"
        else:
            explanation += "✗ Cryptographic validation: FAILED\n"
        
        # Layer 3: Intent
        if intent_result.intent_match:
            explanation += f"✓ Intent analysis: {intent_result.intent.value} matches {intent_result.mission_phase.value} phase\n"
        else:
            explanation += f"✗ Intent mismatch: {intent_result.reason}\n"
        
        # Layer 4: Behavior
        if behavior_result.anomaly_level in ["NONE", "LOW"]:
            explanation += f"✓ Behavioral analysis: Normal pattern (score {behavior_result.behavior_score})\n"
        else:
            explanation += f"✗ Behavioral anomaly: {behavior_result.anomaly_level} - {behavior_result.explanation}\n"
        
        # Layer 5: Shadow execution
        if shadow_result.trajectory_risk < 0.3:
            explanation += f"✓ Trajectory prediction: Safe (risk {shadow_result.trajectory_risk})\n"
        else:
            explanation += f"✗ Trajectory prediction: {shadow_result.explanation}\n"
        
        # Final reasoning
        explanation += f"\n{decision_result.explanation}\n"
        
        # Actionable outcome
        if decision == "ACCEPT":
            explanation += "\n→ Command forwarded to flight controller\n"
        elif decision == "CONSTRAIN":
            explanation += "\n→ Command modified and forwarded with constraints\n"
        elif decision == "HOLD":
            explanation += "\n→ Command queued pending operator review\n"
        elif decision == "RTL":
            explanation += "\n→ EMERGENCY: RTL command issued to flight controller\n"
        
        return explanation
    
    def log_decision(self,
                    command_obj,
                    decision_result,
                    intent_result,
                    behavior_result,
                    shadow_result,
                    crypto_valid: bool):
        """
        Log complete decision to all formats
        
        1. Human-readable text
        2. Machine-readable JSONL
        3. Audit trail JSONL
        """
        self.command_counter += 1
        timestamp = datetime.now().isoformat()
        
        # 1. Human explanation
        human_text = self.generate_human_explanation(
            command_obj,
            decision_result,
            intent_result,
            behavior_result,
            shadow_result,
            crypto_valid
        )
        
        # Write to human log
        with open(self.human_log, "a", encoding='utf-8') as f:
            f.write(f"\n[Command #{self.command_counter}] {timestamp}\n")
            f.write("-" * 80 + "\n")
            f.write(human_text)
            f.write("-" * 80 + "\n")
        
        # 2. Machine-readable decision log
        decision_record = {
            "session_id": self.session_id,
            "command_id": self.command_counter,
            "timestamp": timestamp,
            "command": {
                "type": command_obj.command_type,
                "source": command_obj.source,
                "params": command_obj.params,
                "sys_id": command_obj.sys_id,
                "comp_id": command_obj.comp_id
            },
            "layers": {
                "crypto": {
                    "valid": crypto_valid
                },
                "intent": intent_result.to_dict(),
                "behavior": behavior_result.to_dict(),
                "shadow": shadow_result.to_dict()
            },
            "decision": decision_result.to_dict()
        }
        
        with open(self.decision_log, "a") as f:
            f.write(json.dumps(decision_record) + "\n")
        
        # 3. Audit trail (immutable, minimal)
        audit_record = {
            "session_id": self.session_id,
            "command_id": self.command_counter,
            "timestamp": timestamp,
            "command_type": command_obj.command_type,
            "decision": decision_result.decision.value,
            "severity": decision_result.severity.value,
            "risk_score": decision_result.contributing_factors["risk_score"],
            "crypto_valid": crypto_valid,
            "geofence_violation": shadow_result.predicted_outcomes.geofence_violation
        }
        
        with open(self.audit_log, "a") as f:
            f.write(json.dumps(audit_record) + "\n")
        
        # Console output (summary)
        self._print_decision_summary(decision_result, self.command_counter)
    
    def _print_decision_summary(self, decision_result, cmd_id):
        """Print color-coded decision summary to console"""
        decision = decision_result.decision.value
        severity = decision_result.severity.value
        risk = decision_result.contributing_factors["risk_score"]
        
        # Color codes
        colors = {
            "ACCEPT": "✅",
            "CONSTRAIN": "⚠️",
            "HOLD": "🔶",
            "RTL": "🚨"
        }
        
        icon = colors.get(decision, "❓")
        
        print(f"\n{icon} [{cmd_id}] Decision: {decision} | Severity: {severity} | Risk: {risk}")
        print(f"   Explanation: {decision_result.explanation[:100]}...")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Generate session statistics for post-flight analysis
        """
        # Read all decisions from this session
        decisions = []
        if self.decision_log.exists():
            with open(self.decision_log, "r") as f:
                for line in f:
                    record = json.loads(line)
                    if record["session_id"] == self.session_id:
                        decisions.append(record)
        
        if not decisions:
            return {"session_id": self.session_id, "total_commands": 0}
        
        # Calculate statistics
        total = len(decisions)
        accepted = sum(1 for d in decisions if d["decision"]["decision"] == "ACCEPT")
        constrained = sum(1 for d in decisions if d["decision"]["decision"] == "CONSTRAIN")
        held = sum(1 for d in decisions if d["decision"]["decision"] == "HOLD")
        rtl = sum(1 for d in decisions if d["decision"]["decision"] == "RTL")
        
        crypto_failures = sum(1 for d in decisions if not d["layers"]["crypto"]["valid"])
        intent_mismatches = sum(1 for d in decisions if not d["layers"]["intent"]["intent_match"])
        high_behavior_anomalies = sum(1 for d in decisions if d["layers"]["behavior"]["anomaly_level"] in ["HIGH", "MEDIUM"])
        geofence_violations = sum(1 for d in decisions if d["layers"]["shadow"]["predicted_outcomes"]["geofence_violation"])
        
        avg_risk = sum(d["decision"]["contributing_factors"]["risk_score"] for d in decisions) / total
        
        return {
            "session_id": self.session_id,
            "total_commands": total,
            "decisions": {
                "ACCEPT": accepted,
                "CONSTRAIN": constrained,
                "HOLD": held,
                "RTL": rtl
            },
            "percentages": {
                "accepted_pct": round(100 * accepted / total, 1),
                "blocked_pct": round(100 * (held + rtl) / total, 1)
            },
            "layer_detections": {
                "crypto_failures": crypto_failures,
                "intent_mismatches": intent_mismatches,
                "behavior_anomalies": high_behavior_anomalies,
                "geofence_violations": geofence_violations
            },
            "average_risk_score": round(avg_risk, 2)
        }
    
    def print_session_summary(self):
        """Print session summary to console and file"""
        summary = self.get_session_summary()
        
        print("\n" + "="*80)
        print("SESSION SUMMARY")
        print("="*80)
        print(f"Session ID: {summary['session_id']}")
        print(f"Total Commands: {summary['total_commands']}")
        print(f"\nDecisions:")
        print(f"  ✅ ACCEPT:     {summary['decisions']['ACCEPT']}")
        print(f"  ⚠️  CONSTRAIN:  {summary['decisions']['CONSTRAIN']}")
        print(f"  🔶 HOLD:       {summary['decisions']['HOLD']}")
        print(f"  🚨 RTL:        {summary['decisions']['RTL']}")
        print(f"\nAcceptance Rate: {summary['percentages']['accepted_pct']}%")
        print(f"Block Rate: {summary['percentages']['blocked_pct']}%")
        print(f"\nLayer Detections:")
        print(f"  Crypto Failures:       {summary['layer_detections']['crypto_failures']}")
        print(f"  Intent Mismatches:     {summary['layer_detections']['intent_mismatches']}")
        print(f"  Behavior Anomalies:    {summary['layer_detections']['behavior_anomalies']}")
        print(f"  Geofence Violations:   {summary['layer_detections']['geofence_violations']}")
        print(f"\nAverage Risk Score: {summary['average_risk_score']}")
        print("="*80)
        
        # Write to file
        summary_file = self.log_dir / f"summary_{self.session_id}.json"
        with open(summary_file, "w") as f:
            json.dumps(summary, indent=2)
        
        print(f"\n📊 Full summary saved to: {summary_file}")


def main():
    """Test explainable logger"""
    logger = ExplainableLogger()
    
    # Mock objects for testing
    class MockCommand:
        command_type = "NAVIGATION"
        source = "gcs"
        params = {"lat": 47.0, "lon": -122.0, "alt": 50}
        sys_id = 255
        comp_id = 0
        timestamp = time.time()
    
    class MockIntent:
        intent = type('obj', (object,), {'value': 'NAVIGATION'})
        confidence = 0.85
        intent_match = True
        mission_phase = type('obj', (object,), {'value': 'MISSION'})
        reason = "Intent matches mission phase"
        def to_dict(self): return {"intent": "NAVIGATION", "confidence": 0.85}
    
    class MockBehavior:
        behavior_score = 0.25
        anomaly_level = "LOW"
        explanation = "Normal behavior"
        def to_dict(self): return {"behavior_score": 0.25, "anomaly_level": "LOW"}
    
    class MockShadow:
        trajectory_risk = 0.2
        explanation = "Trajectory appears safe"
        predicted_outcomes = type('obj', (object,), {
            'geofence_violation': False,
            'to_dict': lambda: {"geofence_violation": False}
        })
        def to_dict(self): return {"trajectory_risk": 0.2}
    
    class MockDecision:
        decision = type('obj', (object,), {'value': 'ACCEPT'})
        severity = type('obj', (object,), {'value': 'NONE'})
        explanation = "All layers report acceptable risk"
        contributing_factors = {"risk_score": 0.22}
        def to_dict(self): return {"decision": "ACCEPT", "severity": "NONE"}
    
    # Log a decision
    logger.log_decision(
        MockCommand(),
        MockDecision(),
        MockIntent(),
        MockBehavior(),
        MockShadow(),
        crypto_valid=True
    )
    
    # Print summary
    logger.print_session_summary()


if __name__ == "__main__":
    main()
