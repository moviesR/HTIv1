# Contributing to HTI-Adapter Harness

HTI is contract-driven: fast safety/control must never be broken by "helpful" changes. Follow these rules to keep timing, safety, and reproducibility intact.

## Prereqs
- Python 3.11, MuJoCo 3.3.6, dm_control (see `requirements.txt`)
- Headless tip: `export MUJOCO_GL=egl`
- Install: `pip install -r requirements.txt`

## Branch & Commit Convention (Conventional Commits)
- `feat(core): last-writer Shield gate`
- `fix(probes): enforce 150ms refractory`
- `perf(predict): cut surrogate p99 to 1.6ms`
- `test(ci): add 10-min soak`
- `docs(readme): dm_control primary`
Keep subjects ≤ 72 chars. Reference issues like `(#123)`.

## Test Matrix (what CI runs)
- OS: Ubuntu 22.04; Python: 3.11; headless EGL
- Commands:
  ```bash
  python tools/validate_system_slice.py configs/system_slice.yaml schemas/system_slice.schema.json
  pytest -q --disable-warnings --maxfail=1
  ```

## Performance/Timing Budgets (hard)

### Bands (p99 ceilings)

| Band | Frame | WCET per cycle | p99 ceiling |
|---|---:|---:|---:|
| **Reflex** | 10 ms (@100 Hz) | ≤ **2 ms** | ≤ **5 ms** |
| **Control** | 20 ms (@50 Hz) | ≤ **6 ms** | ≤ **12 ms** |
| **Predict/Fuse** | 20–100 ms | — | **band p99 ≤ 60 ms** |
| **Semantics** | 200–1000 ms | — | ≤ **800 ms** |
| **Shield** | — | ≤ **1 ms** before actuator write | — |

### Predict/Fuse per-module p99 caps
- Surrogate (XGB / 2-layer MLP ≤10k params): **≤ 2 ms**
- OOD density + conformal residuals: **≤ 2 ms**
- Slip/Contact estimator (≤50k params): **≤ 4 ms**
- Ghost predictor (≤200k params): **≤ 8 ms**
- BO/CMA-ES tick: **≤ 3 ms** (**≤ 40 ms/s**; **≤ 8 proposals/episode**)
- Discrepancy checks: **≤ 2 ms**

### Probe hygiene
- **TTL ≤ 300 ms**, **≤ 2** probes before first action, **refractory 150 ms**

### Adapter bounds (BAC)
- **Δgains** ±10% per TTL
- **v_cap** **tighten-only** (≤ −15% per TTL); auto-relax after stable hold 500 ms
- **μ_comp** ≤ +10% of nominal
- **Offsets** ≤ 1 mm per TTL
- **Rollback** ≤ 1 Control cycle

### Calibration & OOD (if probabilities touch Control)
- **ECE ≤ 0.07** (10 equal-mass bins) **and** **Brier ↓ ≥ 10%** vs uncalibrated
- **Conformal miscoverage ≤ α+2%**; adapt only if **Success LB ≥ θ_s** and **Over-force UB ≤ θ_f**
  - **M0 defaults:** `θ_s = 0.6`, `θ_f = 0.2`, `α = 0.10`

### EventPack
- Fixed window **±300 ms** around event; required fields as in README (t0/t1, hashes, signals, caps, loop p50/p95/p99, risk, discrepancies, AdapterDelta?, ShieldVeto?, Outcome)

## Coding Norms (fast paths)
- **No inter-band locks.** Fast bands never wait for slow ones.
- **Allocation-free** Reflex/Control; deterministic state machines; explicit units.
- Use the **SimClock** (sim time), not wall clock.
- Put constants in **`configs/system_slice.yaml`** (SSOT), not in code.

## PR Checklist (must be green)
- [ ] `configs/system_slice.yaml` validated; **physics_hash** up-to-date
- [ ] **10-minute soaks**: no missed cycles; p99 ≤ caps
- [ ] **Probe hygiene** tests pass (TTL/refractory/≤2-before-action)
- [ ] **Shield last-writer** + **adapter TTL expiry** tests pass
- [ ] **EventPack** ±300 ms window + required fields present
- [ ] If ML touched Control: **calibration (ECE/Brier)** + **conformal** gates pass
- [ ] **README** updated if behavior/limits changed
