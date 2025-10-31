from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional

"""
HTI Environment interface + loaders.

BaseEnv: Minimal contract HTI relies on (no dm_control dependency in tests).
NullEnv: Synthetic, deterministic env for CI/tests.
DmControlEnv: (Later) Real MuJoCo env when assets are added.
"""

# Guarded dm_control import
_DM_CONTROL_AVAILABLE = False
_MJCF_MODULE = None
try:
    from dm_control import mjcf
    from dm_control.mujoco import Physics
    _DM_CONTROL_AVAILABLE = True
    _MJCF_MODULE = mjcf
except ImportError:
    pass

import logging
from pathlib import Path

_logger = logging.getLogger(__name__)

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

# Conditionally define DmControlEnv only if dm_control is available
if _DM_CONTROL_AVAILABLE:
    def _extract_obs(physics: Physics, ee_body_id: int) -> Dict[str, Any]:
        """
        Extract HTI-shaped observations from MuJoCo physics.

        Returns:
            poseEE: [x, y, z] in world frame (meters)
            Fn: Normal force (N), approximated from cfrc_ext
            Ft: Tangential force magnitude (N)
            contact_flags: 1 if EE has contacts, 0 otherwise
        """
        # Get EE position from body xpos (world frame, meters)
        pose_ee = physics.data.xpos[ee_body_id].copy().tolist()

        # Extract contact forces from cfrc_ext (external forces on body)
        # cfrc_ext[body_id] = [fx, fy, fz, tx, ty, tz] in world frame
        f_ext = physics.data.cfrc_ext[ee_body_id, :3]  # Just force components

        # Approximate normal/tangential split (assume z is "up", contact with table)
        Fn = max(0.0, -f_ext[2])  # Normal force (negative z = pressing down on table)
        Ft = float((f_ext[0]**2 + f_ext[1]**2)**0.5)  # Tangential magnitude

        # Contact flags: check if EE has any active contacts
        contact_flags = 0
        for i in range(physics.data.ncon):
            contact = physics.data.contact[i]
            # Check if either geom in contact belongs to EE body
            geom1_body = physics.model.geom_bodyid[contact.geom1]
            geom2_body = physics.model.geom_bodyid[contact.geom2]
            if geom1_body == ee_body_id or geom2_body == ee_body_id:
                contact_flags = 1
                break

        return {
            "poseEE": pose_ee,
            "Fn": float(Fn),
            "Ft": float(Ft),
            "contact_flags": contact_flags
        }

    class DmControlEnv(BaseEnv):
        """
        Real MuJoCo environment using dm_control.

        Loads minimal_world.xml and steps MuJoCo physics, extracting HTI observations.
        Uses mocap control for kinematic EE motion (placeholder for full robot actuation).
        """
        def __init__(self, mjcf_path: str, dt: float, substeps: int):
            self._dt = dt
            self._substeps = substeps
            self._mjcf_path = mjcf_path

            # Load physics
            try:
                self._physics = Physics.from_xml_path(mjcf_path)
                self._ee_body_id = self._physics.model.name2id("ee", "body")
                self._ee_mocap_id = self._physics.model.name2id("ee", "body")  # mocap body
                self._t = 0.0
                self._z_target = 0.72  # Initial EE z position (matches MJCF)
            except Exception as e:
                _logger.error(f"Failed to load MJCF from {mjcf_path}: {e}")
                raise

        def reset(self, seed: int) -> Dict[str, Any]:
            """Reset physics and return initial observation."""
            self._physics.reset()
            self._t = 0.0
            self._z_target = 0.72  # Reset to initial height

            # Set initial mocap position
            mocap_pos = self._physics.data.mocap_pos[0].copy()
            mocap_pos[2] = self._z_target
            self._physics.data.mocap_pos[0] = mocap_pos

            # Step once to settle
            self._physics.step()

            return _extract_obs(self._physics, self._ee_body_id)

        def step(self, action: Dict[str, float]) -> Tuple[Dict[str, Any], bool, Dict[str, Any]]:
            """
            Step physics with action command.

            Action: {"v_cap": float}  # Vertical velocity (m/s)
            Returns: (obs, done, info)
            """
            # Extract velocity command (kinematic placeholder)
            v_cap = float(action.get("v_cap", 0.0))

            # Update target z position (integrate velocity)
            self._z_target += v_cap * self._dt

            # Clamp to reasonable workspace limits (table at 0.7m, max reach ~1.2m)
            self._z_target = max(0.70, min(self._z_target, 1.2))

            # Update mocap target
            mocap_pos = self._physics.data.mocap_pos[0].copy()
            mocap_pos[2] = self._z_target
            self._physics.data.mocap_pos[0] = mocap_pos

            # Step physics for configured substeps
            for _ in range(self._substeps):
                self._physics.step()

            self._t += self._dt

            # Extract observation
            obs = _extract_obs(self._physics, self._ee_body_id)

            # Check done condition (same as NullEnv: lifted above threshold)
            done = obs["poseEE"][2] >= 0.08

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
    Returns DmControlEnv if cfg.env.backend == "DmControlEnv" and dm_control is available.
    Otherwise returns NullEnv (deterministic fallback for CI/tests).

    Gracefully falls back to NullEnv if assets are missing or unloadable.
    """
    backend = cfg.env.backend if hasattr(cfg, 'env') and cfg.env else "NullEnv"

    if backend == "DmControlEnv" and _DM_CONTROL_AVAILABLE:
        # Find asset path relative to this module
        assets_dir = Path(__file__).parent / "assets"
        mjcf_path = assets_dir / "minimal_world.xml"

        if not mjcf_path.exists():
            _logger.warning(
                f"DmControlEnv backend requested but asset not found: {mjcf_path}. "
                f"Falling back to NullEnv."
            )
            return NullEnv(_dt=cfg.physics.dt, _substeps=cfg.physics.substeps)

        try:
            return DmControlEnv(
                mjcf_path=str(mjcf_path),
                dt=cfg.physics.dt,
                substeps=cfg.physics.substeps
            )
        except Exception as e:
            _logger.warning(
                f"Failed to load DmControlEnv from {mjcf_path}: {e}. "
                f"Falling back to NullEnv."
            )
            return NullEnv(_dt=cfg.physics.dt, _substeps=cfg.physics.substeps)

    # Default/fallback: NullEnv
    return NullEnv(_dt=cfg.physics.dt, _substeps=cfg.physics.substeps)

# Legacy compatibility
def make_env(config: Optional[Any] = None) -> Any:
    """
    Legacy factory (deprecated). Use load_from_config() instead.
    Placeholder: returns None until assets and real wrapper are implemented.
    """
    _ = config  # reserved for future use
    return None
