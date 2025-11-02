#!/usr/bin/env python3
"""
Thin runnable harness for PnP_smoke (NullEnv).
Proves end-to-end loop: config → env → scheduler → shield → sampler → success/TTR.

Usage:
    python tools/run_pnp_smoke.py

Not wired to CI; purely for manual validation and demos.
"""
from __future__ import annotations
import time

from hti.core.config import load_system_slice
from hti.core.clock import MonotonicClock
from hti.core.scheduler import BandScheduler
from hti.core.shield import Shield, SafetyCaps
from hti.core.success import detect_lift_success, ttr_ms
from hti.env.dm_env_loader import load_from_config
from hti.io.eventpack import RingBuffer
from hti.io.sampler import Sampler


def main():
    # Load config
    print("[run_pnp_smoke] Loading config...")
    cfg = load_system_slice()

    # Create environment
    print("[run_pnp_smoke] Creating NullEnv...")
    env = load_from_config(cfg)
    env.reset(seed=cfg.seeds.sim_seed)

    # Create clock, ring buffer, sampler
    clk = MonotonicClock()
    ring = RingBuffer(maxlen=512)
    sampler = Sampler(ring, clk.now)

    # Create Shield
    caps = SafetyCaps(
        v_mps=cfg.caps.v_mps,
        a_mps2=cfg.caps.a_mps2,
        fn_N=cfg.caps.fn_N,
        tau_Nm=cfg.caps.tau_Nm,
    )
    shield = Shield(caps)

    # Create scheduler
    sched = BandScheduler(control_hz=cfg.bands.control_hz)

    # Baseline command
    baseline_cmd = {"v_cap": 0.05}  # safe lift velocity

    # Track poses for success detection
    poses = []
    done = False

    def control_fn():
        nonlocal done
        if done:
            return

        # Shield evaluation (baseline → shield → actuator)
        decision = shield.evaluate(proposed_cmd=baseline_cmd, fallback_cmd={"v_cap": 0.0})
        actuated_cmd = decision.final_cmd

        # Step environment
        obs, env_done, info = env.step(actuated_cmd)
        done = env_done

        # Sample to ring buffer
        sampler.sample_env(obs, actuated_cmd)

        # Track pose for success detection
        poses.append(tuple(obs["poseEE"]))

    # Run for ~2 seconds
    print("[run_pnp_smoke] Running Control loop for 2 seconds...")
    sched.start_control(control_fn)
    time.sleep(2.0)
    sched.stop()

    # Detect success and TTR
    print(f"[run_pnp_smoke] Collected {len(poses)} poses")
    success = detect_lift_success(poses, z0=0.02, dz=0.03)
    ttr_val = ttr_ms(poses, dt=env.dt, z0=0.02, dz=0.03)

    print(f"[run_pnp_smoke] Success: {success}")
    print(f"[run_pnp_smoke] TTR: {ttr_val} ms" if ttr_val else "[run_pnp_smoke] TTR: None (no lift)")

    # Acceptance check
    if success and ttr_val and ttr_val <= 400:
        print("[run_pnp_smoke] ✅ PASS: median_TTR_ms_le 400")
    else:
        print("[run_pnp_smoke] ❌ FAIL: did not meet acceptance criteria")

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
