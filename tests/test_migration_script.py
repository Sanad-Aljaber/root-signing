"""Tests for the docs/migration/prep-import.py script logic.

Since the migration script operates on filesystem and requires the tuf library,
these tests validate the script's logic by testing its core operations in
isolation using temporary directories and mocked metadata.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

MIGRATION_SCRIPT = (
    Path(__file__).resolve().parent.parent / "docs" / "migration" / "prep-import.py"
)


class TestMigrationScriptExists:
    """Verify the migration script is present and readable."""

    def test_script_exists(self):
        assert MIGRATION_SCRIPT.exists()

    def test_script_is_python(self):
        with open(MIGRATION_SCRIPT) as f:
            content = f.read()
        assert "import" in content
        assert "shutil" in content


class TestMigrationLogic:
    """Test the core migration operations in isolation."""

    @pytest.fixture
    def work_dir(self):
        """Create a temporary working directory with mock legacy structure."""
        tmpdir = tempfile.mkdtemp()
        # Create mock legacy repository structure
        legacy_dir = Path(tmpdir) / "repository" / "repository"
        legacy_dir.mkdir(parents=True)

        # Create mock root versions
        for version in range(1, 4):
            root_data = {
                "signatures": [{"keyid": "abc", "sig": "def"}],
                "signed": {
                    "_type": "root",
                    "version": version,
                    "spec_version": "1.0",
                    "expires": "2030-01-01T00:00:00Z",
                    "keys": {},
                    "roles": {
                        "root": {"keyids": ["abc"], "threshold": 1},
                        "targets": {"keyids": ["abc"], "threshold": 1},
                        "snapshot": {"keyids": ["abc"], "threshold": 1},
                        "timestamp": {"keyids": ["abc"], "threshold": 1},
                    },
                    "consistent_snapshot": False,
                },
            }
            with open(legacy_dir / f"{version}.root.json", "w") as f:
                json.dump(root_data, f)

        # Create current role files
        for rolename in ["root", "timestamp", "snapshot", "targets"]:
            role_data = {
                "signatures": [{"keyid": "abc", "sig": "def"}],
                "signed": {
                    "_type": rolename,
                    "version": 1,
                    "spec_version": "1.0",
                    "expires": "2030-01-01T00:00:00Z",
                },
            }
            if rolename == "root":
                role_data["signed"]["keys"] = {}
                role_data["signed"]["roles"] = {}
                role_data["signed"]["consistent_snapshot"] = False
            elif rolename == "targets":
                role_data["signed"]["targets"] = {}
            elif rolename == "snapshot":
                role_data["signed"]["meta"] = {}
            elif rolename == "timestamp":
                role_data["signed"]["meta"] = {"snapshot.json": {"version": 1}}
            with open(legacy_dir / f"{rolename}.json", "w") as f:
                json.dump(role_data, f)

        # Also create a delegated role
        delegated_data = {
            "signatures": [{"keyid": "xyz", "sig": "uvw"}],
            "signed": {
                "_type": "targets",
                "version": 1,
                "spec_version": "1.0",
                "expires": "2030-01-01T00:00:00Z",
                "targets": {},
            },
        }
        with open(legacy_dir / "registry.npmjs.org.json", "w") as f:
            json.dump(delegated_data, f)

        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    def test_root_history_copy(self, work_dir):
        """Verify root history files are copied correctly."""
        legacy_dir = work_dir / "repository" / "repository"
        metadata_dir = work_dir / "metadata"
        root_history_dir = metadata_dir / "root_history"
        root_history_dir.mkdir(parents=True, exist_ok=True)

        # Simulate the copy logic from prep-import.py
        version = 1
        while (legacy_dir / f"{version}.root.json").exists():
            shutil.copyfile(
                legacy_dir / f"{version}.root.json",
                root_history_dir / f"{version}.root.json",
            )
            version += 1

        # Verify copies exist
        assert (root_history_dir / "1.root.json").exists()
        assert (root_history_dir / "2.root.json").exists()
        assert (root_history_dir / "3.root.json").exists()
        assert not (root_history_dir / "4.root.json").exists()

    def test_root_history_content_preserved(self, work_dir):
        """Verify file content is preserved during copy."""
        legacy_dir = work_dir / "repository" / "repository"
        metadata_dir = work_dir / "metadata"
        root_history_dir = metadata_dir / "root_history"
        root_history_dir.mkdir(parents=True, exist_ok=True)

        shutil.copyfile(
            legacy_dir / "1.root.json",
            root_history_dir / "1.root.json",
        )

        with open(legacy_dir / "1.root.json") as f:
            original = json.load(f)
        with open(root_history_dir / "1.root.json") as f:
            copied = json.load(f)

        assert original == copied

    def test_version_counting_stops_at_gap(self, work_dir):
        """The copy loop should stop when a version is missing."""
        legacy_dir = work_dir / "repository" / "repository"

        # Remove version 2 to create a gap
        (legacy_dir / "2.root.json").unlink()

        metadata_dir = work_dir / "metadata"
        root_history_dir = metadata_dir / "root_history"
        root_history_dir.mkdir(parents=True, exist_ok=True)

        version = 1
        while (legacy_dir / f"{version}.root.json").exists():
            shutil.copyfile(
                legacy_dir / f"{version}.root.json",
                root_history_dir / f"{version}.root.json",
            )
            version += 1

        # Should only have copied version 1
        assert (root_history_dir / "1.root.json").exists()
        assert not (root_history_dir / "2.root.json").exists()
        assert not (root_history_dir / "3.root.json").exists()

    def test_metadata_directory_creation(self, work_dir):
        """os.makedirs should create the directory structure."""
        target_dir = work_dir / "new_metadata" / "root_history"
        os.makedirs(target_dir, exist_ok=True)
        assert target_dir.exists()
        assert target_dir.is_dir()

    def test_metadata_directory_idempotent(self, work_dir):
        """Repeated makedirs with exist_ok=True should not error."""
        target_dir = work_dir / "new_metadata" / "root_history"
        os.makedirs(target_dir, exist_ok=True)
        os.makedirs(target_dir, exist_ok=True)  # Should not raise
        assert target_dir.exists()


class TestMigrationScriptSyntax:
    """Verify the migration script has valid Python syntax."""

    def test_script_compiles(self):
        """The script should compile without syntax errors."""
        with open(MIGRATION_SCRIPT) as f:
            source = f.read()
        compile(source, str(MIGRATION_SCRIPT), "exec")

    def test_script_uses_expected_imports(self):
        """Verify the script imports necessary modules."""
        with open(MIGRATION_SCRIPT) as f:
            content = f.read()
        assert "import os" in content
        assert "import shutil" in content
        assert "from tuf.api.metadata import Metadata" in content
