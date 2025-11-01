"""
Test geometry hash computation for Phase K.

Verifies that geometry hash changes when MJCF assets are modified.
"""
import tempfile
from pathlib import Path
from tools.validate_system_slice import compute_geometry_hash


def test_geometry_hash_changes_with_asset():
    """Verify that geometry hash changes when XML content changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assets_dir = Path(tmpdir)

        # No assets: should return None
        hash1 = compute_geometry_hash(assets_dir)
        assert hash1 is None

        # Add first asset
        (assets_dir / "test1.xml").write_text("<mujoco><worldbody/></mujoco>")
        hash2 = compute_geometry_hash(assets_dir)
        assert hash2 is not None
        assert len(hash2) == 12  # 12-char digest

        # Add second asset: hash should change
        (assets_dir / "test2.xml").write_text("<mujoco><worldbody><body/></worldbody></mujoco>")
        hash3 = compute_geometry_hash(assets_dir)
        assert hash3 != hash2

        # Modify first asset: hash should change again
        (assets_dir / "test1.xml").write_text("<mujoco><worldbody><geom/></worldbody></mujoco>")
        hash4 = compute_geometry_hash(assets_dir)
        assert hash4 != hash3
        assert hash4 != hash2


def test_geometry_hash_deterministic():
    """Verify that geometry hash is deterministic for same content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assets_dir = Path(tmpdir)

        # Create asset
        (assets_dir / "robot.xml").write_text("<mujoco><worldbody/></mujoco>")

        # Compute hash twice
        hash1 = compute_geometry_hash(assets_dir)
        hash2 = compute_geometry_hash(assets_dir)

        assert hash1 == hash2


def test_minimal_world_xml_hash():
    """Verify that minimal_world.xml has a computable hash."""
    assets_dir = Path(__file__).parent.parent / "hti" / "env" / "assets"

    if not assets_dir.exists():
        # Assets dir doesn't exist yet
        return

    hash_val = compute_geometry_hash(assets_dir)

    if (assets_dir / "minimal_world.xml").exists():
        # minimal_world.xml exists, hash should be computed
        assert hash_val is not None
        assert len(hash_val) == 12
        print(f"minimal_world.xml hash: {hash_val}")
    else:
        # No XML files yet
        assert hash_val is None
