from __future__ import annotations
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from pydantic import BaseModel, Field, field_validator

# --------- Helpers ---------

def _parse_range(v: Union[str, int, float]) -> Tuple[float, float]:
    """
    Accepts "20-50" or numeric; returns (lo, hi) where hi==lo if scalar.
    """
    if isinstance(v, (int, float)):
        f = float(v)
        return (f, f)
    if isinstance(v, str) and "-" in v:
        lo, hi = v.split("-", 1)
        return (float(lo.strip()), float(hi.strip()))
    # Fallback: try float
    return (float(v), float(v))  # may raise ValueError up-stack

# --------- Pydantic Models (typed SSOT) ---------

class PhysicsCfg(BaseModel):
    dt: float
    substeps: int
    solver: str
    tol: float
    contact_margin: float

class SeedsCfg(BaseModel):
    sim_seed: int
    config_hash: str
    physics_hash: str

class BandsCfg(BaseModel):
    reflex_hz: float
    control_hz: float
    predict_hz: Union[str, float] = Field(..., description='e.g., "20-50" or 20')
    semantics_hz: Union[str, float] = Field(..., description='e.g., "1-5" or 2')

    @property
    def predict_range(self) -> Tuple[float, float]:
        return _parse_range(self.predict_hz)

    @property
    def semantics_range(self) -> Tuple[float, float]:
        return _parse_range(self.semantics_hz)

class CapsCfg(BaseModel):
    v_mps: float
    a_mps2: float
    jerk_mps3: float
    fn_N: float
    tau_Nm: float

class ProbesCfg(BaseModel):
    ttl_ms: int = 300
    max_before_action: int = 2
    refractory_ms: int = 150
    dither_hz: List[float] = []

class AcceptanceCfg(BaseModel):
    timing: Dict[str, Any]
    pnp: Optional[Dict[str, Any]] = None
    insertion: Optional[Dict[str, Any]] = None

class RiskCfg(BaseModel):
    tau: float = 0.25
    uncertainty_stub: float = 0.20

class EnvCfg(BaseModel):
    backend: str = "NullEnv"
    fail_fast: bool = True

class SystemSlice(BaseModel):
    engine: str
    physics: PhysicsCfg
    seeds: SeedsCfg
    bands: BandsCfg
    caps: CapsCfg
    probes: ProbesCfg
    randomization: Optional[Dict[str, Any]] = None
    tasks: Optional[Dict[str, Any]] = None
    sensors: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    acceptance: Optional[AcceptanceCfg] = None
    risk: Optional[RiskCfg] = None
    env: Optional[EnvCfg] = None

    @field_validator("engine")
    @classmethod
    def _engine_pin(cls, v: str) -> str:
        if not v.startswith("mujoco-"):
            raise ValueError("engine must be 'mujoco-<version>'")
        return v

# --------- Loader (cached) ---------

@lru_cache(maxsize=1)
def load_system_slice(path: str = "configs/system_slice.yaml") -> SystemSlice:
    """
    Load and type-validate the System Slice once.
    Do NOT call this from Reflex/Control hot paths; pass the object down.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return SystemSlice.model_validate(data)
