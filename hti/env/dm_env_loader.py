from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional

"""
HTI Environment interface + loaders.

BaseEnv: Minimal contract HTI relies on (no dm_control dependency in tests).
NullEnv: Synthetic, deterministic env for CI/tests.
DmControlEnv: (Later) Real MuJoCo env when assets are added.
"""

class BaseEnv:
    """Minimal interface HTI relies on (no dm_control dependency in tests)."""
    def reset(self, seed: int) -> Dict[str, Any]: ...
    def step(self, action: Dict[str, float]) -> Tuple[Dict[str, Any], bool, Dict[str, Any]]: ...
    @property
    def dt(self) -> float: ...
    @property
    def substeps(self) -> int: ...

@dataclass
class NullEnv(BaseEnv):
    """
    Synthetic environment for tests (no MuJoCo dependency).
    Deterministic lift task: z increases with safe v_cap commands.
    """
    _dt: float
    _substeps: int
    _t: float = 0.0
    _z: float = 0.02  # EE height proxy

    def reset(self, seed: int) -> Dict[str, Any]:
        self._t, self._z = 0.0, 0.02
        return {"poseEE": [0.0, 0.0, self._z], "Fn": 0.0, "Ft": 0.0, "contact_flags": 0}

    def step(self, action: Dict[str, float]) -> Tuple[Dict[str, Any], bool, Dict[str, Any]]:
        # Simple "lift if commanded with safe v_cap"
        v = float(action.get("v_cap", 0.0))
        self._z += max(0.0, min(v, 0.25)) * self._dt  # clamp to cap-like behavior
        self._t += self._dt
        obs = {"poseEE": [0.0, 0.0, self._z], "Fn": 0.0, "Ft": 0.0, "contact_flags": 0}
        done = self._z >= 0.08  # arbitrary "lifted" threshold for smoke
        info = {"t": self._t}
        return obs, done, info

    @property
    def dt(self) -> float:
        return self._dt

    @property
    def substeps(self) -> int:
        return self._substeps

def load_from_config(cfg) -> BaseEnv:
    """
    Load environment from HTI config.
    For now always return NullEnv; later: detect presence of assets and return DmControlEnv.
    """
    return NullEnv(_dt=cfg.physics.dt, _substeps=cfg.physics.substeps)

# Legacy compatibility
def make_env(config: Optional[Any] = None) -> Any:
    """
    Legacy factory (deprecated). Use load_from_config() instead.
    Placeholder: returns None until assets and real wrapper are implemented.
    """
    _ = config  # reserved for future use
    return None
