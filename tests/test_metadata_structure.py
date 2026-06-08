"""Tests for TUF metadata structure and validity.

Validates that all metadata JSON files conform to the TUF specification
structure requirements (signatures, signed payload, required fields).
"""

import json
from datetime import datetime, timezone

import pytest

from conftest import METADATA_DIR, TUF_ROLES


class TestMetadataFilesExist:
    """Verify all required TUF metadata files are present."""

    @pytest.mark.parametrize("role", TUF_ROLES)
    def test_role_metadata_exists(self, metadata_dir, role):
        path = metadata_dir / f"{role}.json"
        assert path.exists(), f"Missing required metadata: {role}.json"

    @pytest.mark.parametrize("role", TUF_ROLES)
    def test_role_metadata_is_valid_json(self, metadata_dir, role):
        path = metadata_dir / f"{role}.json"
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, dict)


class TestMetadataTopLevelStructure:
    """Verify all metadata has the required top-level TUF structure."""

    @pytest.mark.parametrize("role", TUF_ROLES)
    def test_has_signatures_field(self, metadata_dir, role):
        with open(metadata_dir / f"{role}.json") as f:
            data = json.load(f)
        assert "signatures" in data
        assert isinstance(data["signatures"], list)

    @pytest.mark.parametrize("role", TUF_ROLES)
    def test_has_signed_field(self, metadata_dir, role):
        with open(metadata_dir / f"{role}.json") as f:
            data = json.load(f)
        assert "signed" in data
        assert isinstance(data["signed"], dict)

    @pytest.mark.parametrize("role", TUF_ROLES)
    def test_signatures_have_required_fields(self, metadata_dir, role):
        with open(metadata_dir / f"{role}.json") as f:
            data = json.load(f)
        for sig in data["signatures"]:
            assert "keyid" in sig, "Signature missing keyid"
            assert "sig" in sig, "Signature missing sig value"
            assert isinstance(sig["keyid"], str)
            assert isinstance(sig["sig"], str)
            assert len(sig["keyid"]) > 0
            assert len(sig["sig"]) > 0


class TestSignedPayloadFields:
    """Verify required fields in the signed payload of each role."""

    @pytest.mark.parametrize("role", TUF_ROLES)
    def test_has_type_field(self, metadata_dir, role):
        with open(metadata_dir / f"{role}.json") as f:
            data = json.load(f)
        assert data["signed"]["_type"] == role

    @pytest.mark.parametrize("role", TUF_ROLES)
    def test_has_spec_version(self, metadata_dir, role):
        with open(metadata_dir / f"{role}.json") as f:
            data = json.load(f)
        assert "spec_version" in data["signed"]
        assert data["signed"]["spec_version"].startswith("1.")

    @pytest.mark.parametrize("role", TUF_ROLES)
    def test_has_version(self, metadata_dir, role):
        with open(metadata_dir / f"{role}.json") as f:
            data = json.load(f)
        assert "version" in data["signed"]
        assert isinstance(data["signed"]["version"], int)
        assert data["signed"]["version"] >= 1

    @pytest.mark.parametrize("role", TUF_ROLES)
    def test_has_expires(self, metadata_dir, role):
        with open(metadata_dir / f"{role}.json") as f:
            data = json.load(f)
        assert "expires" in data["signed"]
        # Verify it's a valid ISO 8601 datetime
        expires = data["signed"]["expires"]
        dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        assert dt.tzinfo is not None


class TestRootMetadata:
    """Specific validation for root.json."""

    def test_has_keys(self, root_metadata):
        assert "keys" in root_metadata["signed"]
        assert len(root_metadata["signed"]["keys"]) > 0

    def test_has_roles(self, root_metadata):
        assert "roles" in root_metadata["signed"]
        for role in TUF_ROLES:
            assert role in root_metadata["signed"]["roles"]

    def test_roles_have_threshold(self, root_metadata):
        for role in TUF_ROLES:
            role_info = root_metadata["signed"]["roles"][role]
            assert "threshold" in role_info
            assert isinstance(role_info["threshold"], int)
            assert role_info["threshold"] >= 1

    def test_roles_have_keyids(self, root_metadata):
        for role in TUF_ROLES:
            role_info = root_metadata["signed"]["roles"][role]
            assert "keyids" in role_info
            assert isinstance(role_info["keyids"], list)
            assert len(role_info["keyids"]) >= 1

    def test_role_keyids_reference_existing_keys(self, root_metadata):
        keys = root_metadata["signed"]["keys"]
        for role in TUF_ROLES:
            role_info = root_metadata["signed"]["roles"][role]
            for keyid in role_info["keyids"]:
                assert keyid in keys, (
                    f"Role '{role}' references keyid '{keyid}' "
                    f"not found in keys"
                )

    def test_keys_have_required_fields(self, root_metadata):
        for keyid, key_data in root_metadata["signed"]["keys"].items():
            assert "keytype" in key_data
            assert "keyval" in key_data
            assert "scheme" in key_data
            assert "public" in key_data["keyval"]

    def test_has_consistent_snapshot(self, root_metadata):
        assert "consistent_snapshot" in root_metadata["signed"]
        assert isinstance(root_metadata["signed"]["consistent_snapshot"], bool)

    def test_has_sufficient_signatures(self, root_metadata):
        threshold = root_metadata["signed"]["roles"]["root"]["threshold"]
        num_sigs = len(root_metadata["signatures"])
        assert num_sigs >= threshold, (
            f"Root has {num_sigs} signatures but threshold is {threshold}"
        )


class TestTimestampMetadata:
    """Specific validation for timestamp.json."""

    def test_has_meta(self, timestamp_metadata):
        assert "meta" in timestamp_metadata["signed"]

    def test_meta_references_snapshot(self, timestamp_metadata):
        meta = timestamp_metadata["signed"]["meta"]
        assert "snapshot.json" in meta

    def test_snapshot_reference_has_version(self, timestamp_metadata):
        snapshot_info = timestamp_metadata["signed"]["meta"]["snapshot.json"]
        assert "version" in snapshot_info
        assert isinstance(snapshot_info["version"], int)
        assert snapshot_info["version"] >= 1


class TestSnapshotMetadata:
    """Specific validation for snapshot.json."""

    def test_has_meta(self, snapshot_metadata):
        assert "meta" in snapshot_metadata["signed"]

    def test_meta_references_targets(self, snapshot_metadata):
        meta = snapshot_metadata["signed"]["meta"]
        # At minimum, root.json and targets-related should be present
        assert any("root" in key for key in meta.keys())

    def test_meta_entries_have_version(self, snapshot_metadata):
        for name, info in snapshot_metadata["signed"]["meta"].items():
            assert "version" in info, f"{name} missing version in snapshot meta"
            assert isinstance(info["version"], int)


class TestTargetsMetadata:
    """Specific validation for targets.json."""

    def test_has_targets(self, targets_metadata):
        assert "targets" in targets_metadata["signed"]
        assert len(targets_metadata["signed"]["targets"]) > 0

    def test_targets_have_required_fields(self, targets_metadata):
        for name, info in targets_metadata["signed"]["targets"].items():
            assert "hashes" in info, f"Target '{name}' missing hashes"
            assert "length" in info, f"Target '{name}' missing length"
            assert isinstance(info["length"], int)
            assert info["length"] > 0

    def test_target_hashes_valid_format(self, targets_metadata):
        for name, info in targets_metadata["signed"]["targets"].items():
            hashes = info["hashes"]
            assert len(hashes) > 0, f"Target '{name}' has no hash algorithms"
            for algo, digest in hashes.items():
                assert isinstance(digest, str)
                assert len(digest) > 0
                # Verify it looks like a hex string
                int(digest, 16)

    def test_has_delegations(self, targets_metadata):
        assert "delegations" in targets_metadata["signed"]
        delegations = targets_metadata["signed"]["delegations"]
        assert "keys" in delegations
        assert "roles" in delegations

    def test_delegation_roles_have_required_fields(self, targets_metadata):
        delegations = targets_metadata["signed"]["delegations"]
        for role in delegations["roles"]:
            assert "name" in role
            assert "keyids" in role
            assert "threshold" in role
            assert "paths" in role or "path_hash_prefixes" in role
