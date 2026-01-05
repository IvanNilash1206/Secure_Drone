"""
Digital Twin Layer (Shadow Execution)

Lightweight kinematic prediction for risk assessment.
NOT full simulation - predicts obvious bad outcomes fast.
"""

from src.digital_twin.shadow_executor import ShadowExecutor, ShadowResult, PredictedOutcome

__all__ = ['ShadowExecutor', 'ShadowResult', 'PredictedOutcome']
