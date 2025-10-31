#!/usr/bin/env python3
"""
Runnable harness for PnP_smoke with DmControlEnv backend.
Demonstrates end-to-end loop with real MuJoCo physics:
  config → DmControlEnv → scheduler → RiskGate → Shield → sampler → success/TTR.

Usage:
    python tools/run_pnp_smoke_dm.py              # Normal run
    python tools/run_pnp_smoke_dm.py --risk-demo  # Demo ABSTAIN behavior

Not wired to CI; requires dm_control installation and assets.
"""
from __future__ import annotations
import argparse
import time
import sys

from hti.core.config import load_system_slice
from hti.core.clock import MonotonicClock
from hti.core.scheduler import BandScheduler
from hti.core.shield import Shield, SafetyCaps
from hti.core.risk import RiskGate
from hti.core.success import detect_lift_success, ttr_ms
from hti.env.dm_env_loader import load_from_config, _DM_CONTROL_AVAILABLE
from hti.io.eventpack import RingBuffer, EventPackAssembler
from hti.io.sampler import Sampler


def main():
    parser = argparse.ArgumentParser(description="Run PnP smoke with DmControlEnv")
    parser.add_argument(
        "--risk-demo",
        action="store_true",
        help="Demo ABSTAIN behavior by setting uncertainty_stub=0.6"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=2.5,
        help="Duration to run in seconds (default: 2.5)"
    )
    args = parser.parse_args()

    if not _DM_CONTROL_AVAILABLE:
        print("[run_pnp_smoke_dm] ERROR: dm_control not available. Install dm_control to run this demo.")
        return 1

    # Load config
    print("[run_pnp_smoke_dm] Loading config...")
    cfg = load_system_slice()

    # Override backend to DmControlEnv
    cfg.env.backend = "DmControlEnv"

    # Risk demo: boost uncertainty to trigger ABSTAIN
    if args.risk_demo:
        print("[run_pnp_smoke_dm] RISK DEMO: Setting uncertainty_stub=0.6 (will trigger ABSTAIN)")
        cfg.risk.uncertainty_stub = 0.6

    # Create environment
    print(f"[run_pnp_smoke_dm] Creating env (backend={cfg.env.backend})...")
    env = load_from_config(cfg)

    if type(env).__name__ != "DmControlEnv":
        print("[run_pnp_smoke_dm] WARNING: DmControlEnv not loaded (falling back to NullEnv)")
        print(f"[run_pnp_smoke_dm] Actual backend: {type(env).__name__}")

    env.reset(seed=cfg.seeds.sim_seed)

    # Create clock, ring buffer, sampler
    clk = MonotonicClock()
    ring = RingBuffer(maxlen=512)
    sampler = Sampler(ring, clk.now)

    # Create EventPack assembler
    ep_asm = EventPackAssembler(ring, clk.now)

    # Create RiskGate
    risk_gate = RiskGate(tau=cfg.risk.tau, uncertainty_stub=cfg.risk.uncertainty_stub)

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

    # Track poses and counters
    poses = []
    done = False
    counters = {"abstain": 0, "veto": 0, "ttl_expired": 0}

    def control_fn():
        nonlocal done
        if done:
            return

        # Get current observation (from last step)
        obs_samples = ring.get_window(-0.01, 0.01)  # tiny window to get latest
        if not obs_samples:
            # First step: use reset obs
            obs = env.reset(seed=cfg.seeds.sim_seed)
        else:
            # Use latest observation payload
            _, obs = obs_samples[-1]

        # RiskGate evaluation
        risk_decision = risk_gate.decide(obs, baseline_cmd, caps)

        # If risk gate says ABSTAIN, clamp command to zero
        if risk_decision["decision"] == "abstain":
            counters["abstain"] += 1
            cmd_after_risk = {"v_cap": 0.0}
        else:
            cmd_after_risk = baseline_cmd

        # Shield evaluation (risk-gated cmd → shield → actuator)
        decision = shield.evaluate(proposed_cmd=cmd_after_risk, fallback_cmd={"v_cap": 0.0})
        actuated_cmd = decision.final_cmd

        if not decision.accepted:
            counters["veto"] += 1

        # Step environment
        obs, env_done, info = env.step(actuated_cmd)
        done = env_done

        # Sample to ring buffer
        sampler.sample_env(obs, actuated_cmd)

        # Track pose for success detection
        poses.append(tuple(obs["poseEE"]))

    # Run for configured duration
    print(f"[run_pnp_smoke_dm] Running Control loop for {args.duration} seconds...")
    sched.start_control(control_fn)
    time.sleep(args.duration)
    sched.stop()

    # Detect success and TTR
    print(f"[run_pnp_smoke_dm] Collected {len(poses)} poses")
    success = detect_lift_success(poses, z0=0.02, dz=0.03)
    ttr_val = ttr_ms(poses, dt=env.dt, z0=0.02, dz=0.03)

    print(f"[run_pnp_smoke_dm] Backend: {type(env).__name__}")
    print(f"[run_pnp_smoke_dm] Samples: {len(poses)}")
    print(f"[run_pnp_smoke_dm] Success: {success}")
    print(f"[run_pnp_smoke_dm] TTR: {ttr_val} ms" if ttr_val else "[run_pnp_smoke_dm] TTR: None (no lift)")
    print(f"[run_pnp_smoke_dm] Counters: abstain={counters['abstain']}, veto={counters['veto']}, ttl_expired={counters['ttl_expired']}")

    # Assemble final EventPack to demonstrate metadata
    if poses:
        trigger_t = clk.now()
        env_meta = {
            "backend": type(env).__name__,
            "dt": env.dt,
            "substeps": env.substeps
        }

        # Get latest risk assessment
        obs_samples = ring.get_window(-0.01, 0.01)
        if obs_samples:
            _, obs = obs_samples[-1]
            risk_decision = risk_gate.decide(obs, baseline_cmd, caps)
            risk_meta = {
                "U": risk_decision["U"],
                "H": risk_decision["H"],
                "r": risk_decision["risk"]
            }
        else:
            risk_meta = None

        ep = ep_asm.assemble(trigger_t, counters=counters, env_meta=env_meta, risk=risk_meta)
        print(f"[run_pnp_smoke_dm] EventPack meta: {ep.meta}")

    # Acceptance check
    if args.risk_demo:
        if counters["abstain"] > 0:
            print(f"[run_pnp_smoke_dm] ✅ RISK DEMO PASS: ABSTAIN triggered {counters['abstain']} times")
        else:
            print("[run_pnp_smoke_dm] ⚠️  RISK DEMO: No ABSTAIN events (tau may be too high)")
    else:
        if success and ttr_val and ttr_val <= 400:
            print("[run_pnp_smoke_dm] ✅ PASS: median_TTR_ms_le 400")
        else:
            print("[run_pnp_smoke_dm] ❌ FAIL: did not meet acceptance criteria")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
