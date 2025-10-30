# HTI-Adapter Harness (dm_control-primary)

**Make robots learn without breaking things.**
Translate high-level intent into **bounded, verifiable control deltas** under hard real-time guarantees — or **ABSTAIN** when risk is high.

> **HTI = Hierarchical Temporal Intelligence**
> Fast safety/control (100–50 Hz) is strictly separated from slower fusion/semantics (10–1 Hz). The **Safety Shield** is last-writer before actuators.

---

## Environment stance

* **Primary:** **Manipulator-MuJoCo (dm_control template)** on **MuJoCo 3.3.6**
  Precise step control, low overhead, clean access to contact/forces → perfect for HTI timing, event-packs, and probe hygiene.
* **Sidecar (later):** **robosuite** for cross-paper benchmarks/demos after HTI-M0 is green.
* **Not now:** MuJoCo Playground/MJX (only if you later need large batched RL).

---

## Core guarantees (non-negotiables)

* **Time bands (p99 ceilings):**
  Reflex ~100 Hz (10 ms frame, WCET ≤ 2 ms, p99 ≤ 5 ms)
  Control ~50 Hz (20 ms frame, WCET ≤ 6 ms, p99 ≤ 12 ms)
  Predict/Fuse 10–50 Hz (**band p99 ≤ 60 ms**; per-module caps below)
  Semantics 1–5 Hz (p99 ≤ 800 ms; shed first)
  **Shield** (always): executes ≤ 1 ms before actuator write; **last-writer-wins**

* **Safety invariants**

  * No inter-band locks; fast bands never wait for slow ones
  * Monotonic clocks; CI fails on any deadline miss
  * **Bounded adapters:** caps + **TTL ≤ 500 ms**, rollback ≤ 1 Control cycle
  * **Calibration:** any probability touching Control must meet **ECE ≤ 0.07** (10 equal-mass bins) and **Brier ↓ ≥ 10%** vs uncalibrated
  * **Abstain** outside support (OOD/conformal fail) or when **risk** (r = \text{uncertainty} \times \text{hazard}) ≥ τ (default **0.25**)

---

## Repo layout

```
hti-adapter-harness/
├─ configs/
│  └─ system_slice.yaml              # SSOT for physics, tasks, caps
├─ schemas/
│  └─ system_slice.schema.json       # JSON Schema (CI hard gate)
├─ hti/
│  ├─ core/      (clock, rate, shield, adapter)
│  ├─ predict/   (surrogate/OOD/conformal/search stubs)
│  ├─ probes/    (probe engine; TTL/refractory/≤2-before-action)
│  ├─ io/        (ring buffer + EventPack)
│  └─ env/
│     ├─ dm_env_loader.py            # dm_control wrapper
│     └─ assets/ur5e_parallel_worn.xml
├─ tools/
│  └─ validate_system_slice.py
├─ tests/
│  ├─ test_timing_soak.py            # 10-min p99 soaks (100/50 Hz)
│  ├─ test_probe_hygiene.py
│  ├─ test_band_isolation.py
│  ├─ test_shield.py                 # last-writer gate
│  ├─ test_adapter_ttl.py
│  ├─ test_eventpack_window.py       # ±300 ms window + required fields
│  └─ metrics.py                     # CVaR@α definition & tests
└─ .github/workflows/ci.yml
```

---

## Quickstart (dm_control)

**Pins**

```
mujoco==3.3.6
dm-control>=1.0
numpy>=1.26
pydantic>=2.8
jsonschema>=4.23
pytest>=8.2
```

**Setup**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# If dm_control wheels for your OS/Python lag, build it against MuJoCo 3.3.6.
```

**Run M0 loop (sim-time, fixed-step)**

```bash
python main_dm_control.py  # uses hti/env/assets/ur5e_parallel_worn.xml
```

**Validate System Slice & run CI tests locally**

```bash
python tools/validate_system_slice.py configs/system_slice.yaml schemas/system_slice.schema.json
pytest -q --disable-warnings --maxfail=1
```

> **Red blocks merges:** schema mismatch, physics hash drift, p99 over caps, missed cycles, probe/TTL violations, Shield not last-writer, or incorrect CVaR.

---

## System Slice (SSOT)

All runs are governed by `configs/system_slice.yaml`. Change it, or it didn’t happen.

**Key fields (dm_control-tuned)**

```yaml
engine: mujoco-3.3.6
physics: { dt: 0.005, substeps: 1, solver: PGS, tol: 1e-6, contact_margin: 0.001 }
seeds: { sim_seed: 1337, config_hash: "$GIT_SHA", physics_hash: "<filled by validator>" }
bands: { reflex_hz: 100, control_hz: 50, predict_hz: 20-50, semantics_hz: 1-5 }
caps:  { v_mps: 0.25, a_mps2: 1.0, jerk_mps3: 5.0, fn_N: 12, tau_Nm: 6 }
tasks:
  PnP_smoke: { objs: "cube/sphere × rubber/plastic", pos_jitter_m: 0.03, yaw_deg: 10 }
  Insertion:
    tight: { peg_mm: 10.00, hole_mm: 10.05 }
    chamfered: { peg_mm: 12.00, hole_mm: 12.20 }
    init_error: { lateral_mm: 0.5, angular_deg: 1.0 }
probes: { ttl_ms: 300, max_before_action: 2, refractory_ms: 150, dither_hz: [5,12] }
randomization:
  motor_lag_ms: [0,8,15]
  table_mu: [0.3,0.6,0.9]
  tol_mm_jitter: 0.02
  control_jitter_ms: 0.5
acceptance:
  timing:   { soak_min: 10, p99_under_caps: true, missed_cycles: 0 }
  pnp:      { median_TTR_ms_le: 400, cap_hits: 0, trials: 50 }
  insertion:{ chamfered_success_ge: 0.70, tight_success_ge: 0.40, overforce_exceedances: 0 }
```

Run the validator once; copy the printed `physics_hash` into the YAML. CI will fail if physics drifts.

---

## Per-module WCET caps (Predict/Fuse)

| Module                                      |                                   p99 cap |
| ------------------------------------------- | ----------------------------------------: |
| Surrogate (XGB/2-layer MLP ≤ 10k params)    |                                **≤ 2 ms** |
| OOD density + conformal residuals           |                                **≤ 2 ms** |
| Slip/Contact estimator (tiny CNN/TCN ≤ 50k) |                                **≤ 4 ms** |
| Ghost predictor (≤ 200k params)             |                                **≤ 8 ms** |
| BO/CMA-ES tick (bounded)                    | **≤ 3 ms** (≤ 40 ms/s; ≤ 8 props/episode) |
| Discrepancy checks                          |                                **≤ 2 ms** |

**Band total:** Predict/Fuse **p99 ≤ 60 ms** → breach = auto-rollback + CI fail.

---

## Risk ladder & shedding

[
r = \text{uncertainty} \times \text{hazard}, \quad \tau = 0.25
]

* (r<0.10): baseline only
* (0.10\le r<0.25): one light action (one surrogate **or** one micro-probe)
* (0.25\le r<0.50): short-horizon forecast; **defer Semantics**
* (r\ge0.50): **ABSTAIN or Shield-limit**; safety probes only
  **Shed order:** Semantics → Predict extras → Predict core → (never shed Reflex/Control/Shield)

---

## Adapter bounds (BAC)

* **Δgains:** ±10% per TTL (hysteresis on engagement)
* **v_cap:** **tighten-only** (≤ −15% per TTL); auto-relax after stable hold 500 ms
* **μ_comp:** +10% of nominal; never exceed Shield caps
* **Offsets:** ≤ 1 mm per TTL (if enabled)
* **TTL:** 300 ms default, 500 ms max; **rollback ≤ 1 Control cycle**

---

## EventPack (audit log)

Fixed window **±300 ms** around event/probe. Required fields include:
`t0,t1, config_hash, physics_hash, sim_seed, band_clocks, signals{q,dq,τ_cmd,τ_est,i_motor,poseEE,Fn,Ft,contact_flags}, caps{force,torque,vel,accel,jerk}, loop_p50/p95/p99{reflex,control}, missed_cycles, risk{U,H,r}, discrepancy_types[], AdapterDelta?, ShieldVeto?, Outcome{success,overforce,ttr_ms}`

---

## Benchmarks (later)

* **robosuite** tasks (e.g., pick-place, door) imported as **external benchmarks** once M0 is green. They do **not** drive your HTI timing/tests.

---

## Safety

**Never** deploy on real hardware without conservative caps, E-stop, and supervision. This repo is designed to **fail fast** in CI to prevent dangerous drift.

---

## License

MIT

---

If you want this as a PR-ready patch instead, I can format it as a unified diff against your current README.
