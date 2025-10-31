from __future__ import annotations
from typing import Dict, Any
from hti.core.shield import SafetyCaps

"""
RiskGate: Deterministic risk = uncertainty × hazard with ABSTAIN capability.
No ML; uncertainty is a config stub until Predict/Fuse lands.
"""

class RiskGate:
    """
    Risk gate for Control band: decide ACCEPT or ABSTAIN based on risk = U × H.
    ABSTAIN before Shield if risk ≥ tau.
    """
    def __init__(self, tau: float, uncertainty_stub: float):
        """
        Args:
            tau: Risk threshold (abstain if risk ≥ tau)
            uncertainty_stub: Fixed uncertainty value (M0 stub, no ML)
        """
        self._tau = tau
        self._uncertainty_stub = uncertainty_stub

    def compute_hazard(self, obs: Dict[str, Any], cmd: Dict[str, Any], caps: SafetyCaps) -> float:
        """
        Hazard = max ratio to caps you're requesting/operating near.
        M0: only v_cap available in NullEnv.

        Args:
            obs: Environment observation
            cmd: Proposed command
            caps: Safety caps

        Returns:
            Hazard in [0, ∞); ≤1 is low hazard
        """
        # Velocity hazard: ratio of commanded v_cap to cap
        h_v = max(0.0, cmd.get("v_cap", 0.0) / caps.v_mps) if caps.v_mps > 0 else 0.0

        # Later: add Fn hazard when dm_control available
        # h_fn = max(0.0, obs.get("Fn", 0.0) / caps.fn_N) if caps.fn_N > 0 else 0.0

        hazard = max(h_v, 0.0)
        return hazard

    def uncertainty(self, obs: Dict[str, Any]) -> float:
        """
        M0 stub: return fixed uncertainty from config.
        Later: replace with OOD detector, conformal residuals, etc.

        Args:
            obs: Environment observation (unused in stub)

        Returns:
            Uncertainty value
        """
        _ = obs  # reserved for future OOD detector
        return self._uncertainty_stub

    def decide(self, obs: Dict[str, Any], cmd: Dict[str, Any], caps: SafetyCaps) -> Dict[str, Any]:
        """
        Decide ACCEPT or ABSTAIN based on risk threshold.

        Args:
            obs: Environment observation
            cmd: Proposed command
            caps: Safety caps

        Returns:
            Decision dict with {"decision": "accept"|"abstain", "risk": r, "U": u, "H": h}
        """
        U = self.uncertainty(obs)
        H = self.compute_hazard(obs, cmd, caps)
        r = U * H

        decision = "abstain" if r >= self._tau else "accept"

        return {
            "decision": decision,
            "risk": r,
            "U": U,
            "H": H,
        }
