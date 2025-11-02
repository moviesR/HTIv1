#!/usr/bin/env python3
"""
Validate HTI System Slice configuration against JSON Schema and enforce a physics hash.

Usage:
  python tools/validate_system_slice.py configs/system_slice.yaml schemas/system_slice.schema.json [--strict]

Behavior:
  - Validates YAML against the schema.
  - Computes a deterministic physics_hash from the 'physics' dict.
  - If seeds.physics_hash == "<FILL_ME>":
        * prints the computed hash
        * exits 0 by default (so bootstrapping passes)
        * exits 1 if --strict is provided
  - If seeds.physics_hash != computed hash: exits 1.
  - Otherwise exits 0.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_geometry_hash(assets_dir: Path) -> str | None:
    """
    Compute deterministic hash of all .xml files in assets directory.
    Returns None if directory doesn't exist or has no .xml files.
    """
    if not assets_dir.exists():
        return None

    xml_files = sorted(assets_dir.glob("*.xml"))
    if not xml_files:
        return None

    hasher = hashlib.sha256()
    for xml_path in xml_files:
        # Include filename and content for determinism
        hasher.update(xml_path.name.encode("utf-8"))
        hasher.update(xml_path.read_bytes())

    return hasher.hexdigest()[:12]


def compute_physics_hash(physics_dict: dict, geometry_hash: str | None = None) -> str:
    """
    12-char SHA256 digest of canonicalized physics dict.
    If geometry_hash is provided, it's included in the digest.
    """
    if geometry_hash:
        # Combine physics config + geometry hash
        combined = {"physics": physics_dict, "geometry": geometry_hash}
        return hashlib.sha256(_canon(combined)).hexdigest()[:12]
    else:
        return hashlib.sha256(_canon(physics_dict)).hexdigest()[:12]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("config_path", type=Path)
    ap.add_argument("schema_path", type=Path)
    ap.add_argument("--strict", action="store_true", help="Fail if physics_hash is <FILL_ME> (bootstrapping gate).")
    args = ap.parse_args()

    # Load config (YAML) and schema (JSON)
    try:
        cfg = yaml.safe_load(args.config_path.read_text())
    except Exception as e:
        print(f"[validator] ERROR: failed to read YAML: {e}", file=sys.stderr)
        return 1
    try:
        schema = json.loads(args.schema_path.read_text())
    except Exception as e:
        print(f"[validator] ERROR: failed to read schema: {e}", file=sys.stderr)
        return 1

    # Schema validation
    v = Draft202012Validator(schema)
    errors = sorted(v.iter_errors(cfg), key=lambda e: e.path)
    if errors:
        print("[validator] SCHEMA FAIL:")
        for e in errors:
            loc = "/".join([str(p) for p in e.path]) or "(root)"
            print(f"  - at {loc}: {e.message}")
        return 1
    print("[validator] schema: OK")

    # Physics hash check (include geometry hash if backend is DmControlEnv)
    physics = cfg.get("physics", {})
    env_cfg = cfg.get("env", {})
    backend = env_cfg.get("backend", "NullEnv")

    geometry_hash = None
    if backend == "DmControlEnv":
        assets_dir = args.config_path.parent.parent / "hti" / "env" / "assets"
        geometry_hash = compute_geometry_hash(assets_dir)
        if geometry_hash:
            print(f"[validator] geometry_hash = {geometry_hash} (from {assets_dir})")
        else:
            print(f"[validator] note: DmControlEnv backend but no assets found in {assets_dir}")

    computed = compute_physics_hash(physics, geometry_hash)
    seeds = cfg.get("seeds", {})
    configured = seeds.get("physics_hash", "")

    if configured == "<FILL_ME>":
        print(f"[validator] computed physics_hash = {computed}")
        if args.strict:
            print("[validator] STRICT mode: fill seeds.physics_hash and re-run.")
            return 1
        else:
            print("[validator] non-strict bootstrapping: pass (will enforce once filled).")
            return 0

    if configured != computed:
        print(f"[validator] physics_hash mismatch: configured={configured} computed={computed}")
        return 1

    print("[validator] physics_hash: OK")
    print("[validator] VALIDATION OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
