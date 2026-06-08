"""Tests for TUF root metadata history chain.

Validates that the root_history directory contains a complete, sequential
chain of root metadata versions with proper structure and continuity.
"""

import json

import pytest

from conftest import METADATA_DIR, ROOT_HISTORY_DIR


class TestRootHistoryExists:
    """Verify root history directory and files exist."""

    def test_root_history_directory_exists(self, root_history_dir):
        assert root_history_dir.exists()
        assert root_history_dir.is_dir()

    def test_root_history_not_empty(self, root_history_dir):
        files = list(root_history_dir.glob("*.root.json"))
        assert len(files) > 0, "Root history directory is empty"

    def test_root_history_files_naming(self, root_history_dir):
        """All files should match N.root.json pattern."""
        for path in root_history_dir.iterdir():
            if path.suffix == ".json":
                parts = path.name.split(".")
                assert len(parts) == 3, f"Unexpected filename: {path.name}"
                assert parts[1] == "root"
                assert parts[2] == "json"
                int(parts[0])  # Must be parseable as integer


class TestRootHistoryChain:
    """Verify root history forms a complete sequential chain."""

    def test_chain_starts_at_version_1(self, all_root_history):
        assert 1 in all_root_history, "Root history must start at version 1"

    def test_chain_is_sequential(self, all_root_history):
        """No gaps in version numbers."""
        versions = sorted(all_root_history.keys())
        expected = list(range(versions[0], versions[-1] + 1))
        assert versions == expected, (
            f"Gap in root history versions. "
            f"Expected {expected}, got {versions}"
        )

    def test_versions_match_filenames(self, all_root_history):
        """The version field inside each file matches the filename version."""
        for version, data in all_root_history.items():
            inner_version = data["signed"]["version"]
            assert inner_version == version, (
                f"File {version}.root.json has inner version {inner_version}"
            )

    def test_all_versions_are_root_type(self, all_root_history):
        for version, data in all_root_history.items():
            assert data["signed"]["_type"] == "root", (
                f"Version {version} has type '{data['signed']['_type']}'"
            )

    def test_all_versions_have_signatures(self, all_root_history):
        for version, data in all_root_history.items():
            assert len(data["signatures"]) > 0, (
                f"Version {version} has no signatures"
            )

    def test_all_versions_have_keys_and_roles(self, all_root_history):
        for version, data in all_root_history.items():
            signed = data["signed"]
            assert "keys" in signed, f"Version {version} missing keys"
            assert "roles" in signed, f"Version {version} missing roles"
            assert len(signed["keys"]) > 0
            assert len(signed["roles"]) > 0


class TestRootHistoryConsistency:
    """Verify consistency between current root.json and root_history."""

    def test_latest_history_matches_current_root(
        self, root_metadata, all_root_history
    ):
        """The latest version in history should match the current root.json."""
        latest_version = max(all_root_history.keys())
        latest_history = all_root_history[latest_version]

        assert root_metadata["signed"]["version"] == latest_version, (
            f"Current root.json version {root_metadata['signed']['version']} "
            f"does not match latest history version {latest_version}"
        )

    def test_current_root_version_in_history(
        self, root_metadata, root_history_dir
    ):
        """Current root.json version should have a corresponding history file."""
        version = root_metadata["signed"]["version"]
        expected_file = root_history_dir / f"{version}.root.json"
        assert expected_file.exists(), (
            f"No history file for current root version {version}"
        )


class TestRootHistoryKeyRotation:
    """Verify key rotation properties in root history."""

    def test_spec_version_consistency(self, all_root_history):
        """All root versions should use TUF spec version 1.x."""
        for version, data in all_root_history.items():
            if "spec_version" in data["signed"]:
                spec = data["signed"]["spec_version"]
                assert spec.startswith("1."), (
                    f"Version {version} uses unexpected spec {spec}"
                )

    def test_root_role_always_present(self, all_root_history):
        """Every root version must define the 'root' role."""
        for version, data in all_root_history.items():
            roles = data["signed"]["roles"]
            assert "root" in roles, (
                f"Version {version} missing 'root' role definition"
            )

    def test_root_threshold_always_positive(self, all_root_history):
        """Root role threshold must always be >= 1."""
        for version, data in all_root_history.items():
            threshold = data["signed"]["roles"]["root"]["threshold"]
            assert threshold >= 1, (
                f"Version {version} has root threshold {threshold}"
            )
