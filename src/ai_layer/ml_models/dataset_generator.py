"""
Training Dataset Generator

Generates synthetic labeled dataset for intent inference model training.

Data sources:
1. Simulated normal flight missions (SITL)
2. Attack scenarios (MITM, replay, logic anomalies)
3. Operator error patterns
4. Edge cases and failure modes

Output:
- Feature vectors (37-dim) with labels
- Train/val/test splits by flight session
- Balanced class distribution
- Includes high-risk and adversarial examples
"""

import numpy as np
import pandas as pd
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter

from src.ai_layer.feature_extractor_v2 import (
    FeatureExtractorV2,
    CommandContext,
    mavlink_to_context
)
from src.ai_layer.intent_labels import (
    IntentClass,
    IntentLabeler,
    IntentLabel
)


class FlightScenarioGenerator:
    """
    Generates realistic flight command sequences
    
    Scenarios:
    - Normal waypoint mission
    - Takeoff and landing
    - Mode transitions
    - Emergency RTL
    - Parameter adjustments
    - Attack patterns (MITM, replay, logic bombs)
    """
    
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        self.scenario_templates = {
            'normal_mission': self._generate_normal_mission,
            'takeoff_landing': self._generate_takeoff_landing,
            'mode_transitions': self._generate_mode_transitions,
            'emergency_rtl': self._generate_emergency_rtl,
            'parameter_tuning': self._generate_parameter_tuning,
            'mitm_attack': self._generate_mitm_attack,
            'replay_attack': self._generate_replay_attack,
            'logic_anomaly': self._generate_logic_anomaly,
            'rapid_command_flood': self._generate_command_flood,
            'unauthorized_disarm': self._generate_unauthorized_disarm,
        }
    
    def generate_scenarios(self, n_each: int = 50) -> List[Dict[str, Any]]:
        """
        Generate multiple scenarios of each type
        
        Returns list of flight sessions, each with command sequence + metadata
        """
        sessions = []
        
        for scenario_name, generator_func in self.scenario_templates.items():
            print(f"Generating {n_each} '{scenario_name}' scenarios...")
            
            for i in range(n_each):
                session = generator_func(session_id=f"{scenario_name}_{i}")
                sessions.append(session)
        
        print(f"✅ Generated {len(sessions)} flight sessions")
        return sessions
    
    def _generate_normal_mission(self, session_id: str) -> Dict[str, Any]:
        """Normal autonomous waypoint mission"""
        commands = []
        t = time.time()
        
        # ARM
        commands.append(self._create_command(
            'ARM_DISARM', t, 1.0, flight_mode='GUIDED', armed=False,
            battery=0.95, altitude=0.0, velocity=0.0
        ))
        t += 2.0
        
        # Takeoff to 30m
        commands.append(self._create_command(
            'TAKEOFF', t, 30.0, flight_mode='GUIDED', armed=True,
            battery=0.94, altitude=0.0, velocity=0.0
        ))
        t += 15.0
        
        # Switch to AUTO
        commands.append(self._create_command(
            'SET_MODE', t, 3.0, flight_mode='AUTO', armed=True,
            battery=0.92, altitude=30.0, velocity=5.0, mission_phase='CRUISE'
        ))
        t += 2.0
        
        # Navigate waypoints
        for i in range(5):
            wp_alt = 25.0 + np.random.uniform(-5, 5)
            commands.append(self._create_command(
                'SET_POSITION_TARGET', t, wp_alt,
                flight_mode='AUTO', armed=True,
                battery=0.9 - i*0.05, altitude=wp_alt, velocity=8.0,
                mission_phase='WAYPOINT'
            ))
            t += np.random.uniform(10, 20)
        
        # RTL
        commands.append(self._create_command(
            'RTL', t, 0.0, flight_mode='RTL', armed=True,
            battery=0.65, altitude=28.0, velocity=6.0, mission_phase='NONE'
        ))
        t += 25.0
        
        # Land
        commands.append(self._create_command(
            'LAND', t, 0.0, flight_mode='LAND', armed=True,
            battery=0.6, altitude=5.0, velocity=1.0, mission_phase='LANDING'
        ))
        t += 10.0
        
        # Disarm
        commands.append(self._create_command(
            'ARM_DISARM', t, 0.0, flight_mode='LAND', armed=True,
            battery=0.58, altitude=0.0, velocity=0.0
        ))
        
        return {
            'session_id': session_id,
            'scenario_type': 'normal_mission',
            'is_attack': False,
            'commands': commands,
            'metadata': {'description': 'Normal waypoint mission with RTL'}
        }
    
    def _generate_mitm_attack(self, session_id: str) -> Dict[str, Any]:
        """MITM attack: injected malicious commands during flight"""
        commands = []
        t = time.time()
        
        # Normal start
        commands.append(self._create_command(
            'ARM_DISARM', t, 1.0, flight_mode='GUIDED', armed=False,
            battery=0.95, altitude=0.0
        ))
        t += 2.0
        
        commands.append(self._create_command(
            'TAKEOFF', t, 30.0, flight_mode='GUIDED', armed=True,
            battery=0.94, altitude=0.0
        ))
        t += 15.0
        
        # Cruise
        commands.append(self._create_command(
            'SET_POSITION_TARGET', t, 30.0, flight_mode='AUTO', armed=True,
            battery=0.9, altitude=30.0, velocity=8.0, mission_phase='CRUISE'
        ))
        t += 10.0
        
        # 🚨 INJECTED: Sudden altitude change to 100m (outside geofence)
        commands.append(self._create_command(
            'SET_POSITION_TARGET', t, 100.0, flight_mode='AUTO', armed=True,
            battery=0.88, altitude=30.0, velocity=8.0, mission_phase='CRUISE',
            is_malicious=True
        ))
        t += 0.5
        
        # 🚨 INJECTED: Rapid mode change
        commands.append(self._create_command(
            'SET_MODE', t, 0.0, flight_mode='MANUAL', armed=True,
            battery=0.88, altitude=35.0, velocity=12.0, mission_phase='CRUISE',
            is_malicious=True
        ))
        t += 1.0
        
        # Defensive RTL (operator)
        commands.append(self._create_command(
            'RTL', t, 0.0, flight_mode='RTL', armed=True,
            battery=0.87, altitude=38.0, velocity=10.0
        ))
        
        return {
            'session_id': session_id,
            'scenario_type': 'mitm_attack',
            'is_attack': True,
            'commands': commands,
            'metadata': {'description': 'MITM injected altitude and mode commands'}
        }
    
    def _generate_replay_attack(self, session_id: str) -> Dict[str, Any]:
        """Replay attack: repeated commands out of context"""
        commands = []
        t = time.time()
        
        # Normal cruise
        for i in range(3):
            commands.append(self._create_command(
                'SET_POSITION_TARGET', t, 25.0, flight_mode='AUTO', armed=True,
                battery=0.8, altitude=25.0, velocity=7.0, mission_phase='CRUISE'
            ))
            t += 12.0
        
        # 🚨 REPLAY: Same ARM command repeated 5 times rapidly (should only happen once)
        for i in range(5):
            commands.append(self._create_command(
                'ARM_DISARM', t, 1.0, flight_mode='AUTO', armed=True,  # Already armed!
                battery=0.75, altitude=25.0, velocity=7.0, mission_phase='CRUISE',
                is_malicious=True
            ))
            t += 0.2  # Rapid succession
        
        # Continue normally
        commands.append(self._create_command(
            'RTL', t, 0.0, flight_mode='RTL', armed=True,
            battery=0.7, altitude=25.0, velocity=7.0
        ))
        
        return {
            'session_id': session_id,
            'scenario_type': 'replay_attack',
            'is_attack': True,
            'commands': commands,
            'metadata': {'description': 'Replayed ARM commands during flight'}
        }
    
    def _generate_logic_anomaly(self, session_id: str) -> Dict[str, Any]:
        """Logic anomaly: commands that violate operational logic"""
        commands = []
        t = time.time()
        
        # Normal takeoff
        commands.append(self._create_command(
            'ARM_DISARM', t, 1.0, flight_mode='GUIDED', armed=False,
            battery=0.95, altitude=0.0
        ))
        t += 2.0
        
        commands.append(self._create_command(
            'TAKEOFF', t, 30.0, flight_mode='GUIDED', armed=True,
            battery=0.94, altitude=0.0
        ))
        t += 15.0
        
        # 🚨 ANOMALY: DISARM at 30m altitude (motors would cut = crash)
        commands.append(self._create_command(
            'ARM_DISARM', t, 0.0, flight_mode='GUIDED', armed=True,
            battery=0.92, altitude=30.0, velocity=5.0,
            is_malicious=True
        ))
        t += 1.0
        
        # 🚨 ANOMALY: TAKEOFF while already airborne
        commands.append(self._create_command(
            'TAKEOFF', t, 50.0, flight_mode='GUIDED', armed=False,  # Not even armed
            battery=0.91, altitude=30.0, velocity=0.0,
            is_malicious=True
        ))
        
        return {
            'session_id': session_id,
            'scenario_type': 'logic_anomaly',
            'is_attack': True,
            'commands': commands,
            'metadata': {'description': 'Logically invalid command sequence'}
        }
    
    def _generate_command_flood(self, session_id: str) -> Dict[str, Any]:
        """Rapid command flooding (DoS pattern)"""
        commands = []
        t = time.time()
        
        # Normal start
        commands.append(self._create_command(
            'ARM_DISARM', t, 1.0, flight_mode='GUIDED', armed=False,
            battery=0.95, altitude=0.0
        ))
        t += 2.0
        
        # 🚨 FLOOD: 50 commands in 2 seconds
        for i in range(50):
            commands.append(self._create_command(
                'SET_POSITION_TARGET', t, 30.0 + i*0.1, flight_mode='GUIDED',
                armed=True, battery=0.9, altitude=10.0, velocity=3.0,
                is_malicious=True
            ))
            t += 0.04  # 25 commands/second
        
        return {
            'session_id': session_id,
            'scenario_type': 'command_flood',
            'is_attack': True,
            'commands': commands,
            'metadata': {'description': 'Rapid command flooding'}
        }
    
    def _generate_unauthorized_disarm(self, session_id: str) -> Dict[str, Any]:
        """Unauthorized disarm during critical phase"""
        commands = []
        t = time.time()
        
        # Takeoff
        commands.append(self._create_command(
            'ARM_DISARM', t, 1.0, flight_mode='GUIDED', armed=False,
            battery=0.95, altitude=0.0
        ))
        t += 2.0
        
        commands.append(self._create_command(
            'TAKEOFF', t, 30.0, flight_mode='GUIDED', armed=True,
            battery=0.94, altitude=0.0
        ))
        t += 8.0
        
        # 🚨 Mid-takeoff disarm (at 15m altitude = crash)
        commands.append(self._create_command(
            'ARM_DISARM', t, 0.0, flight_mode='GUIDED', armed=True,
            battery=0.92, altitude=15.0, velocity=3.0, mission_phase='TAKEOFF',
            is_malicious=True
        ))
        
        return {
            'session_id': session_id,
            'scenario_type': 'unauthorized_disarm',
            'is_attack': True,
            'commands': commands,
            'metadata': {'description': 'Disarm during takeoff'}
        }
    
    # Simplified generators for other scenarios
    def _generate_takeoff_landing(self, session_id: str) -> Dict[str, Any]:
        """Simple takeoff and landing"""
        return self._generate_normal_mission(session_id)  # Reuse
    
    def _generate_mode_transitions(self, session_id: str) -> Dict[str, Any]:
        """Multiple mode changes"""
        commands = []
        t = time.time()
        modes = ['STABILIZE', 'GUIDED', 'AUTO', 'LOITER', 'RTL', 'LAND']
        
        for i, mode in enumerate(modes):
            commands.append(self._create_command(
                'SET_MODE', t, float(i), flight_mode=mode, armed=True,
                battery=0.9 - i*0.05, altitude=20.0, velocity=5.0
            ))
            t += 5.0
        
        return {
            'session_id': session_id,
            'scenario_type': 'mode_transitions',
            'is_attack': False,
            'commands': commands,
            'metadata': {'description': 'Multiple mode transitions'}
        }
    
    def _generate_emergency_rtl(self, session_id: str) -> Dict[str, Any]:
        """Emergency RTL with low battery"""
        commands = []
        t = time.time()
        
        # Cruise
        commands.append(self._create_command(
            'SET_POSITION_TARGET', t, 30.0, flight_mode='AUTO', armed=True,
            battery=0.25, altitude=30.0, velocity=8.0  # LOW BATTERY
        ))
        t += 5.0
        
        # Emergency RTL
        commands.append(self._create_command(
            'RTL', t, 0.0, flight_mode='RTL', armed=True,
            battery=0.22, altitude=30.0, velocity=8.0
        ))
        
        return {
            'session_id': session_id,
            'scenario_type': 'emergency_rtl',
            'is_attack': False,
            'commands': commands,
            'metadata': {'description': 'Emergency RTL due to low battery'}
        }
    
    def _generate_parameter_tuning(self, session_id: str) -> Dict[str, Any]:
        """Parameter adjustments on ground"""
        commands = []
        t = time.time()
        
        for i in range(5):
            commands.append(self._create_command(
                'PARAM_SET', t, float(i*10), flight_mode='MANUAL', armed=False,
                battery=1.0, altitude=0.0, velocity=0.0
            ))
            t += 3.0
        
        return {
            'session_id': session_id,
            'scenario_type': 'parameter_tuning',
            'is_attack': False,
            'commands': commands,
            'metadata': {'description': 'Parameter tuning on ground'}
        }
    
    def _create_command(self, cmd_type: str, timestamp: float, param1: float,
                       flight_mode: str = 'MANUAL', armed: bool = False,
                       battery: float = 1.0, altitude: float = 0.0,
                       velocity: float = 0.0, mission_phase: str = 'NONE',
                       is_malicious: bool = False) -> Dict[str, Any]:
        """Helper to create command dict"""
        return {
            'msg_id': 76,  # COMMAND_LONG
            'command_type': cmd_type,
            'target_system': 1,
            'target_component': 1,
            'param1': param1,
            'param2': np.random.uniform(-10, 10),
            'param3': np.random.uniform(-10, 10),
            'param4': 0.0,
            'param5': 0.0,
            'param6': 0.0,
            'param7': 0.0,
            'flight_mode': flight_mode,
            'mission_phase': mission_phase,
            'armed': armed,
            'battery_level': battery,
            'altitude': altitude,
            'velocity': velocity,
            'timestamp': timestamp,
            'is_malicious': is_malicious,  # Ground truth for evaluation
        }


class TrainingDatasetBuilder:
    """
    Builds training dataset from flight scenarios
    
    Steps:
    1. Generate flight scenarios
    2. Extract features using FeatureExtractorV2
    3. Label with IntentLabeler
    4. Create train/val/test splits
    5. Save to disk
    """
    
    def __init__(self, output_dir: str = "data/intent_model"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.scenario_gen = FlightScenarioGenerator()
        self.feature_extractor = FeatureExtractorV2(window_size=7)
        self.labeler = IntentLabeler()
    
    def build_dataset(self, n_scenarios_each: int = 50) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Build complete dataset with train/val/test splits
        
        Returns:
            (train_df, val_df, test_df)
        """
        print("🏗️  Building training dataset...")
        
        # Generate scenarios
        sessions = self.scenario_gen.generate_scenarios(n_each=n_scenarios_each)
        
        # Extract features + labels
        all_samples = []
        
        for session in sessions:
            print(f"Processing session: {session['session_id']}")
            
            # Reset feature extractor for new session
            self.feature_extractor.reset()
            
            for cmd in session['commands']:
                # Create CommandContext
                ctx = CommandContext(
                    msg_id=cmd['msg_id'],
                    command_type=cmd['command_type'],
                    target_system=cmd['target_system'],
                    target_component=cmd['target_component'],
                    param1=cmd['param1'],
                    param2=cmd['param2'],
                    param3=cmd['param3'],
                    param4=cmd['param4'],
                    param5=cmd['param5'],
                    param6=cmd['param6'],
                    param7=cmd['param7'],
                    flight_mode=cmd['flight_mode'],
                    mission_phase=cmd['mission_phase'],
                    armed=cmd['armed'],
                    battery_level=cmd['battery_level'],
                    altitude=cmd['altitude'],
                    velocity=cmd['velocity'],
                    timestamp=cmd['timestamp']
                )
                
                # Extract features
                features = self.feature_extractor.extract(ctx)
                
                if features is None:
                    continue  # Skip first command (no history)
                
                # Generate label
                label = self.labeler.label_command(
                    command_ctx={
                        'command_type': cmd['command_type'],
                        'cmd_frequency_1s': features[10],  # temporal feature
                        'param_magnitude': features[6],
                    },
                    vehicle_state={
                        'flight_mode': cmd['flight_mode'],
                        'mission_phase': cmd['mission_phase'],
                        'armed': cmd['armed'],
                        'battery_level': cmd['battery_level'],
                        'altitude': cmd['altitude'],
                        'velocity': cmd['velocity'],
                    }
                )
                
                # Combine into sample
                sample = {
                    'session_id': session['session_id'],
                    'scenario_type': session['scenario_type'],
                    'is_attack': session['is_attack'],
                    'is_malicious_cmd': cmd.get('is_malicious', False),
                    
                    # Features
                    **{f'feature_{i}': features[i] for i in range(len(features))},
                    
                    # Labels
                    'intent': label.intent.value,
                    'intent_index': IntentClass.to_index(label.intent),
                    'risk_score': label.risk_score,
                }
                
                all_samples.append(sample)
        
        # Create DataFrame
        df = pd.DataFrame(all_samples)
        
        print(f"\n✅ Dataset created: {len(df)} samples")
        print(f"   - {df['is_attack'].sum()} attack samples")
        print(f"   - {len(df) - df['is_attack'].sum()} normal samples")
        print(f"\nIntent distribution:")
        print(df['intent'].value_counts())
        
        # Split by session (NOT random - prevent temporal leakage)
        train_df, val_df, test_df = self._split_by_session(df)
        
        # Save to disk
        self._save_dataset(train_df, val_df, test_df)
        
        return train_df, val_df, test_df
    
    def _split_by_session(self, df: pd.DataFrame, 
                         train_ratio: float = 0.7,
                         val_ratio: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split by flight session (not random rows)
        
        This prevents temporal leakage
        """
        sessions = df['session_id'].unique()
        np.random.shuffle(sessions)
        
        n_train = int(len(sessions) * train_ratio)
        n_val = int(len(sessions) * val_ratio)
        
        train_sessions = sessions[:n_train]
        val_sessions = sessions[n_train:n_train + n_val]
        test_sessions = sessions[n_train + n_val:]
        
        train_df = df[df['session_id'].isin(train_sessions)].copy()
        val_df = df[df['session_id'].isin(val_sessions)].copy()
        test_df = df[df['session_id'].isin(test_sessions)].copy()
        
        print(f"\n📊 Dataset splits:")
        print(f"   Train: {len(train_df)} samples from {len(train_sessions)} sessions")
        print(f"   Val:   {len(val_df)} samples from {len(val_sessions)} sessions")
        print(f"   Test:  {len(test_df)} samples from {len(test_sessions)} sessions")
        
        return train_df, val_df, test_df
    
    def _save_dataset(self, train_df: pd.DataFrame, 
                     val_df: pd.DataFrame,
                     test_df: pd.DataFrame):
        """Save datasets to disk"""
        train_df.to_csv(self.output_dir / 'train.csv', index=False)
        val_df.to_csv(self.output_dir / 'val.csv', index=False)
        test_df.to_csv(self.output_dir / 'test.csv', index=False)
        
        # Save metadata
        metadata = {
            'n_features': 37,
            'feature_names': FeatureExtractorV2().feature_names,
            'intent_classes': [ic.value for ic in IntentClass],
            'n_train': len(train_df),
            'n_val': len(val_df),
            'n_test': len(test_df),
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        with open(self.output_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n💾 Dataset saved to: {self.output_dir}")


if __name__ == "__main__":
    # Build dataset
    builder = TrainingDatasetBuilder(output_dir="data/intent_model")
    
    # Generate 30 scenarios of each type (10 scenario types = 300 sessions total)
    train_df, val_df, test_df = builder.build_dataset(n_scenarios_each=30)
    
    print("\n✅ Training dataset generation complete!")
    print(f"\nClass balance in training set:")
    print(train_df['intent'].value_counts(normalize=True))
