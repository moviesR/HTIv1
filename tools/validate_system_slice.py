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


def compute_physics_hash(physics_dict: dict) -> str:
    """12-char SHA256 digest of canonicalized physics dict."""
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

    # Physics hash check
    physics = cfg.get("physics", {})
    computed = compute_physics_hash(physics)
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
