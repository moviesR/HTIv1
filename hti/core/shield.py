from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

"""
Shield = last-writer safety gate executed immediately before actuator write.
Policy (M0): reject (veto) any command that violates hard caps; otherwise accept.
Extension hooks: clamp-to-cap, jerk/accel checks, tighten-only v_cap, force-rate limits.
"""

@dataclass(frozen=True)
class SafetyCaps:
    """Hard ceilings enforced by the Shield (units must match controller)."""
    v_mps: float          # TCP velocity cap
    a_mps2: float         # TCP acceleration cap (not enforced in M0)
    fn_N: float           # Normal force cap
    tau_Nm: float         # Per-joint torque cap (simplified M0: compare to scalar)

@dataclass
class ShieldDecision:
    accepted: bool                 # True=command passes; False=veto → fallback_cmd must be used
    reason: Optional[str] = None   # Why vetoed (or None if accepted)
    final_cmd: Optional[Dict] = None  # Command to actually send to actuators

class Shield:
    """
    Pure Shield evaluator: decide if a proposed command is safe under caps.
    The Control band must call this as the last step each cycle.
    """
    def __init__(self, caps: SafetyCaps):
        self._caps = caps

    def evaluate(self, proposed_cmd: Dict, fallback_cmd: Dict) -> ShieldDecision:
        """
        proposed_cmd: dict with optional fields: {'v_cap', 'fn', 'tau'}
        fallback_cmd: dict to use if veto occurs (e.g., baseline/before-adapter)
        Returns ShieldDecision with final_cmd set to either proposed or fallback.
        """
        # Read proposed values; missing keys are treated as safe defaults
        v = float(proposed_cmd.get("v_cap", 0.0))
        fn = float(proposed_cmd.get("fn", 0.0))
        tau = float(proposed_cmd.get("tau", 0.0))

        if v > self._caps.v_mps:
            return ShieldDecision(False, reason=f"v_cap>{self._caps.v_mps}", final_cmd=fallback_cmd)
        if fn > self._caps.fn_N:
            return ShieldDecision(False, reason=f"fn>{self._caps.fn_N}", final_cmd=fallback_cmd)
        if abs(tau) > self._caps.tau_Nm:
            return ShieldDecision(False, reason=f"|tau|>{self._caps.tau_Nm}", final_cmd=fallback_cmd)

        # NOTE(M0): Acceleration/jerk not enforced; add when trajectory-level info is available.
        return ShieldDecision(True, reason=None, final_cmd=proposed_cmd)

    # Optional clamp path (not used in tests; keep as a hook)
    def clamp(self, proposed_cmd: Dict) -> Tuple[Dict, Dict]:
        """
        Returns (clamped_cmd, info) if you prefer clamping over veto.
        Not used in M0 tests; left as an extension.
        """
        info = {}
        out = dict(proposed_cmd)
        if "v_cap" in out and out["v_cap"] > self._caps.v_mps:
            info["v_cap_clamped_from"] = out["v_cap"]
            out["v_cap"] = self._caps.v_mps
        if "fn" in out and out["fn"] > self._caps.fn_N:
            info["fn_clamped_from"] = out["fn"]
            out["fn"] = self._caps.fn_N
        if "tau" in out and abs(out["tau"]) > self._caps.tau_Nm:
            info["tau_clamped_from"] = out["tau"]
            out["tau"] = max(min(out["tau"], self._caps.tau_Nm), -self._caps.tau_Nm)
        return out, info
