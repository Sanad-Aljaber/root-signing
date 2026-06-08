"""Tests for TUF targets consistency.

Validates that target files referenced in targets metadata actually exist
on disk and have correct properties (hashes, lengths).
"""

import hashlib
import json
from pathlib import Path

import pytest

from conftest import METADATA_DIR, TARGETS_DIR


class TestTargetFilesExist:
    """Verify all targets declared in metadata exist on disk."""

    def test_targets_directory_exists(self, targets_dir):
        assert targets_dir.exists()
        assert targets_dir.is_dir()

    def test_declared_targets_exist_on_disk(self, targets_metadata, targets_dir):
        """Every target in targets.json must have a corresponding file."""
        missing = []
        for target_name in targets_metadata["signed"]["targets"]:
            target_path = targets_dir / target_name
            if not target_path.exists():
                missing.append(target_name)
        assert not missing, (
            f"Targets declared in metadata but missing on disk: {missing}"
        )


class TestTargetHashes:
    """Verify target file hashes match metadata declarations."""

    def _compute_hash(self, filepath, algorithm):
        h = hashlib.new(algorithm)
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def test_target_sha256_hashes(self, targets_metadata, targets_dir):
        """Verify SHA-256 hashes for all targets that declare them."""
        mismatches = []
        for target_name, info in targets_metadata["signed"]["targets"].items():
            target_path = targets_dir / target_name
            if not target_path.exists():
                continue
            hashes = info.get("hashes", {})
            if "sha256" in hashes:
                actual = self._compute_hash(target_path, "sha256")
                expected = hashes["sha256"]
                if actual != expected:
                    mismatches.append(
                        f"{target_name}: expected {expected}, got {actual}"
                    )
        assert not mismatches, (
            f"SHA-256 hash mismatches:\n" + "\n".join(mismatches)
        )

    def test_target_sha512_hashes(self, targets_metadata, targets_dir):
        """Verify SHA-512 hashes for all targets that declare them."""
        mismatches = []
        for target_name, info in targets_metadata["signed"]["targets"].items():
            target_path = targets_dir / target_name
            if not target_path.exists():
                continue
            hashes = info.get("hashes", {})
            if "sha512" in hashes:
                actual = self._compute_hash(target_path, "sha512")
                expected = hashes["sha512"]
                if actual != expected:
                    mismatches.append(
                        f"{target_name}: expected {expected}, got {actual}"
                    )
        assert not mismatches, (
            f"SHA-512 hash mismatches:\n" + "\n".join(mismatches)
        )


class TestTargetLengths:
    """Verify target file lengths match metadata declarations."""

    def test_target_lengths(self, targets_metadata, targets_dir):
        """File sizes must match the declared length."""
        mismatches = []
        for target_name, info in targets_metadata["signed"]["targets"].items():
            target_path = targets_dir / target_name
            if not target_path.exists():
                continue
            expected_length = info["length"]
            actual_length = target_path.stat().st_size
            if actual_length != expected_length:
                mismatches.append(
                    f"{target_name}: expected {expected_length} bytes, "
                    f"got {actual_length}"
                )
        assert not mismatches, (
            f"Length mismatches:\n" + "\n".join(mismatches)
        )


class TestDelegatedTargets:
    """Verify delegated target metadata."""

    def test_delegated_metadata_files_exist(
        self, targets_metadata, metadata_dir
    ):
        """Delegated role metadata files should exist."""
        delegations = targets_metadata["signed"].get("delegations", {})
        roles = delegations.get("roles", [])
        for role in roles:
            role_name = role["name"]
            role_path = metadata_dir / f"{role_name}.json"
            assert role_path.exists(), (
                f"Delegated role '{role_name}' metadata not found"
            )

    def test_delegated_metadata_valid_json(
        self, targets_metadata, metadata_dir
    ):
        """Delegated role metadata must be valid JSON."""
        delegations = targets_metadata["signed"].get("delegations", {})
        roles = delegations.get("roles", [])
        for role in roles:
            role_name = role["name"]
            role_path = metadata_dir / f"{role_name}.json"
            if role_path.exists():
                with open(role_path) as f:
                    data = json.load(f)
                assert "signatures" in data
                assert "signed" in data

    def test_delegated_targets_exist(self, targets_metadata, metadata_dir, targets_dir):
        """Targets declared in delegated roles should exist on disk."""
        delegations = targets_metadata["signed"].get("delegations", {})
        roles = delegations.get("roles", [])
        for role in roles:
            role_name = role["name"]
            role_path = metadata_dir / f"{role_name}.json"
            if not role_path.exists():
                continue
            with open(role_path) as f:
                role_data = json.load(f)
            role_targets = role_data["signed"].get("targets", {})
            for target_name in role_targets:
                target_path = targets_dir / target_name
                assert target_path.exists(), (
                    f"Delegated target '{target_name}' from "
                    f"role '{role_name}' not found"
                )


class TestTrustedRoot:
    """Validate the trusted_root.json target structure."""

    @pytest.fixture
    def trusted_root(self, targets_dir):
        path = targets_dir / "trusted_root.json"
        if not path.exists():
            pytest.skip("trusted_root.json not present")
        with open(path) as f:
            return json.load(f)

    def test_trusted_root_has_media_type(self, trusted_root):
        assert "mediaType" in trusted_root
        assert "sigstore" in trusted_root["mediaType"]

    def test_trusted_root_has_certificate_authorities(self, trusted_root):
        assert "certificateAuthorities" in trusted_root
        assert len(trusted_root["certificateAuthorities"]) > 0

    def test_trusted_root_has_tlogs(self, trusted_root):
        assert "tlogs" in trusted_root
        assert len(trusted_root["tlogs"]) > 0

    def test_trusted_root_has_ctlogs(self, trusted_root):
        assert "ctlogs" in trusted_root
        assert len(trusted_root["ctlogs"]) > 0

    def test_trusted_root_has_timestamp_authorities(self, trusted_root):
        assert "timestampAuthorities" in trusted_root
        assert len(trusted_root["timestampAuthorities"]) > 0

    def test_tlog_entries_valid(self, trusted_root):
        for tlog in trusted_root["tlogs"]:
            assert "baseUrl" in tlog
            assert "logId" in tlog
            assert "publicKey" in tlog or "certificates" in tlog

    def test_certificate_authorities_valid(self, trusted_root):
        for ca in trusted_root["certificateAuthorities"]:
            assert "certChain" in ca
            assert "certificates" in ca["certChain"]
            assert len(ca["certChain"]["certificates"]) > 0
