# HTI-Adapter Harness (dm_control primary)

Translate high-level intent into **bounded, verifiable control deltas** under hard real-time guarantees — or **ABSTAIN** when risk is high.

> **HTI = Hierarchical Temporal Intelligence.**
> Fast safety/control (100–50 Hz) is strictly separated from slower fusion/semantics (10–1 Hz). A **Safety Shield** is the last writer before actuators.

---

## What this repo is

* **Adapter harness** that enforces timing, safety, and audit guarantees for manipulation in simulation.
* **M0 scope:** sim-only, UR5-class arm with worn two-finger gripper (MuJoCo), pick-and-place + insertion tasks, fixed caps, and CI-enforced contracts.

---

## Environment stance

* **Primary:** **Manipulator-MuJoCo (dm_control template)** on **MuJoCo 3.3.6**
  Precise step control, low overhead, clean access to contacts/forces → ideal for HTI timing, event-packs, and probe hygiene.
* **Sidecar (later):** **robosuite** for cross-paper benchmarks/demos after HTI-M0 is green.
* **Not now:** MuJoCo Playground / MJX (only if you later need large batched RL).

---

## Core guarantees (non-negotiables)

**Time bands (p99 ceilings & WCET caps)**

* **Reflex:** ~100 Hz (10 ms frame; **WCET ≤ 2 ms**, **p99 ≤ 5 ms**)
* **Control:** ~50 Hz (20 ms frame; **WCET ≤ 6 ms**, **p99 ≤ 12 ms**)
* **Predict/Fuse:** 10–50 Hz (**band total p99 ≤ 60 ms**; per-module caps below)
* **Semantics:** 1–5 Hz (**p99 ≤ 800 ms**; shed first)
* **Shield:** executes ≤ 1 ms before actuator write; **last-writer-wins**

**Safety invariants**

* No inter-band locks; fast bands never wait for slow ones.
* Monotonic clocks; **CI fails on any deadline miss**.
* **Bounded adapters:** caps + **TTL ≤ 500 ms**, rollback ≤ 1 Control cycle.
* **Calibration:** any probability touching Control must meet **ECE ≤ 0.07** (10 equal-mass bins) and **Brier ↓ ≥ 10%** vs uncalibrated.
* **Abstain** outside support (OOD/conformal fail) or when **risk** exceeds τ.

**Risk definition**

* Plain: `risk = uncertainty × hazard`, default threshold `τ = 0.25`.
* LaTeX: [ r = \text{uncertainty} \times \text{hazard},\quad \tau = 0.25 ]

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
# If dm_control wheels lag for your OS/Python, build against MuJoCo 3.3.6.
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

**CI hard-fails on:** schema mismatch, physics-hash drift, p99 over caps, missed cycles, probe/TTL violations, Shield not last-writer, CVaR spec violations.

---

## M0 System Slice (SSOT)

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

> Run the validator once and copy the printed `physics_hash` into the YAML. CI will fail if physics drifts.

---

## Per-module WCET caps (Predict/Fuse)

| Module                                      |                                   p99 cap |
| ------------------------------------------- | ----------------------------------------: |
| Surrogate (XGB / 2-layer MLP ≤ 10k params)  |                                **≤ 2 ms** |
| OOD density + conformal residuals           |                                **≤ 2 ms** |
| Slip/Contact estimator (tiny CNN/TCN ≤ 50k) |                                **≤ 4 ms** |
| Ghost predictor (≤ 200k params)             |                                **≤ 8 ms** |
| BO/CMA-ES tick (bounded)                    | **≤ 3 ms** (≤ 40 ms/s; ≤ 8 props/episode) |
| Discrepancy checks                          |                                **≤ 2 ms** |

**Band total:** Predict/Fuse **p99 ≤ 60 ms** → breach = auto-rollback + CI fail.

---

## Risk ladder & shedding

* ( r = \text{uncertainty} \times \text{hazard},\quad \tau = 0.25 )

* `r < 0.10`: baseline only

* `0.10 ≤ r < 0.25`: one light action (one surrogate **or** one micro-probe)

* `0.25 ≤ r < 0.50`: short-horizon forecast; **defer Semantics**

* `r ≥ 0.50`: **ABSTAIN or Shield-limit**; safety probes only

**Shed order:** Semantics → Predict extras → Predict core → *(never shed Reflex/Control/Shield)*

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

## OOD & health

* Conformal / density OOD on Predict, abstain on fail.
* Promote sensors to **advisory-only** on calibration expiry or novelty spikes.
* CI includes timing soaks and probe hygiene to prevent drift.

---

## Benchmarks (later)

* **robosuite** tasks (e.g., pick-place, door) imported as **external benchmarks** once M0 is green. They do **not** drive HTI timing/tests.

---

## Safety

**Never** deploy on real hardware without conservative caps, E-stop, and supervision. This repo is designed to **fail fast** in CI to prevent dangerous drift.

---

## License

MIT

It’s strong—clean, aligned with the dm_control pivot, and it keeps the HTI contract front-and-center. I’d ship it with a few surgical tweaks so new contributors don’t miss critical steps and the safety gates are fully executable.

# High-impact tweaks (succinct)

1. **Pin physics explicitly in Quickstart:** add the “compute & paste `physics_hash`” step so CI won’t false-fail.
2. **Headless dm_control note:** tell folks to set `MUJOCO_GL=egl` (or `osmesa`) to avoid GL issues on servers.
3. **Make the risk formula render everywhere:** use a code fence instead of pseudo-LaTeX in Markdown.
4. **Lock OOD/conformal thresholds:** add typical M0 numbers (`θ_s=0.6`, `θ_f=0.2`, `α=0.1`) so “OOD & health” is actionable.
5. **Anchor loop rates to sim step:** state that dt=0.005 → Reflex each step (100 Hz), Control every 2 steps (50 Hz).
6. **Mention BO budget explicitly:** keep `≤40 ms/s` and `≤8 proposals/episode` with the table (you already have it; I just mirrored it into prose under Predict/Fuse).
7. **Tiny copy nit:** “dm_control primary” → “dm_control-primary” for title consistency.
8. **Add a one-liner about no inter-band locks in Contributing:** prevents “helpful” async awaits.

````diff
@@
-# HTI-Adapter Harness (dm_control primary)
+# HTI-Adapter Harness (dm_control-primary)
@@
 **Run M0 loop (sim-time, fixed-step)**
 
 ```bash
 python main_dm_control.py  # uses hti/env/assets/ur5e_parallel_worn.xml
````

-**Validate System Slice & run CI tests locally**
+**Validate System Slice & run CI tests locally**

```bash
python tools/validate_system_slice.py configs/system_slice.yaml schemas/system_slice.schema.json
pytest -q --disable-warnings --maxfail=1
```

-**CI hard-fails on:** schema mismatch, physics-hash drift, p99 over caps, missed cycles, probe/TTL violations, Shield not last-writer, CVaR spec violations.
+> First run will print a `physics_hash`. Paste that value into `seeds.physics_hash` in `configs/system_slice.yaml`, re-run the validator, then run tests.
+
+**CI hard-fails on:** schema mismatch, physics-hash drift, p99 over caps, missed cycles, probe/TTL violations, Shield not last-writer, CVaR spec violations.
+
+**Headless tip:** set `MUJOCO_GL=egl` (or `osmesa`) when running on servers without a display:
+`export MUJOCO_GL=egl`
@@
-**Key fields (dm_control-tuned)**
+**Key fields (dm_control-tuned)**

```yaml
engine: mujoco-3.3.6
physics: { dt: 0.005, substeps: 1, solver: PGS, tol: 1e-6, contact_margin: 0.001 }
@@
```

-> Run the validator once and copy the printed `physics_hash` into the YAML. CI will fail if physics drifts.
+> Run the validator once and copy the printed `physics_hash` into the YAML. CI will fail if physics drifts.
+
+**Rate anchoring:** with `dt=0.005` and `substeps=1`, **Reflex** runs every step (**100 Hz**), **Control** every 2 steps (**50 Hz**). No wall-clock sleeps; timing is sim-time.
@@
-## Risk ladder & shedding
--------------------------

-* ( r = \text{uncertainty} \times \text{hazard},\quad \tau = 0.25 )
+## Risk ladder & shedding
+
+`
+risk = uncertainty × hazard
+τ = 0.25
+`
@@
**Shed order:** Semantics → Predict extras → Predict core → *(never shed Reflex/Control/Shield)*
@@

## EventPack (audit log)

@@

## OOD & health

-* Conformal / density OOD on Predict, abstain on fail.
+* Conformal / density OOD on Predict, abstain on fail. Permit adaptation only if **Success LB ≥ θ_s** and **Over-force UB ≤ θ_f** with miscoverage ≤ **α+2%** on a hold-out split.

* * **M0 defaults:** `θ_s = 0.6`, `θ_f = 0.2`, `α = 0.10`

- Promote sensors to **advisory-only** on calibration expiry or novelty spikes.
- CI includes timing soaks and probe hygiene to prevent drift.

````

# Optional “Contributing” stub (prevents timing regressions)
Drop this at the end if you want:

```md
## Contributing

- No inter-band locks. Do not `await` or block Control/Reflex on Predict/Fuse or Semantics.
- Keep fast paths allocation-free and deterministic.
- Any module that influences Control with probabilities must ship calibration (ECE ≤ 0.07, Brier ↓ ≥ 10%).
- Changes to physics, caps, or probes must update `configs/system_slice.yaml` and pass schema + physics_hash validation.
````
