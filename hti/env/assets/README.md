# HTI Environment Assets

This directory contains MJCF (MuJoCo XML) files for physical robot environments used by the HTI harness.

## Directory Structure

```
hti/env/assets/
├── README.md                          # This file
├── ur5e_parallel_worn.xml             # (Pending) UR5e + worn parallel gripper MJCF
└── [additional asset files]           # Meshes, textures, referenced XMLs
```

## Geometry Hash

When `env.backend = "DmControlEnv"` in the system config, the validator computes a **geometry hash** from all `.xml` files in this directory:

1. All `.xml` files are sorted alphabetically
2. For each file: hash(filename + file_contents)
3. Combined into a 12-character SHA256 digest
4. Merged with the physics hash to detect drift in both config **and** geometry

This ensures that changes to robot morphology, gripper geometry, or contact properties trigger validation failures, preventing silent drift.

## Asset Targets

### Phase 1: UR5e + Worn Parallel Gripper

**Target morphology:**
- UR5e arm (6 DOF)
- Worn parallel-jaw gripper (force-controlled)
- Contact-rich insertion task with clearance ≤0.5mm

**File naming:**
- Primary MJCF: `ur5e_parallel_worn.xml`
- Referenced meshes: `meshes/` subdirectory
- Textures/materials: `textures/` subdirectory (if needed)

**Contact model requirements:**
- Worn contact surfaces (beveled edges, chamfers)
- Friction cone: μ ∈ [0.4, 0.8] (typical metal-on-metal)
- Contact solver: pyramidal approximation, ≥4 substeps

### Phase 2: Additional Environments (Future)

- Compliant insertion (spring-loaded peg)
- Multi-object pick-and-place
- Deformable contact (cable routing)

## Usage in HTI

When `backend = "DmControlEnv"`:

```python
from hti.core.config import load_system_slice
from hti.env.dm_env_loader import load_from_config

cfg = load_system_slice("configs/system_slice.yaml")
env = load_from_config(cfg)  # Returns DmControlEnv if dm_control available

obs = env.reset(seed=42)
for _ in range(100):
    action = {"v_cap": 0.05}  # Safe velocity command
    obs, done, info = env.step(action)
```

## Validation

The validator enforces geometry hash integrity:

```bash
python tools/validate_system_slice.py \
    configs/system_slice.yaml \
    schemas/system_slice.schema.json \
    --strict
```

If assets change, update `seeds.physics_hash` in the config to match the new computed hash.

## Adding New Assets

1. Place `.xml` file(s) in this directory
2. Run validator to compute new geometry hash
3. Update `seeds.physics_hash` in config
4. Commit both assets and config together (atomic update)
5. CI will enforce hash match on all future PRs

---

**Status:** Placeholder (assets not yet added)
**Next step:** Add `ur5e_parallel_worn.xml` MJCF and enable geometry hashing
