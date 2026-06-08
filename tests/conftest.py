"""Shared fixtures for root-signing repository tests."""

import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = REPO_ROOT / "metadata"
TARGETS_DIR = REPO_ROOT / "targets"
ROOT_HISTORY_DIR = METADATA_DIR / "root_history"

TUF_ROLES = ("root", "timestamp", "snapshot", "targets")


@pytest.fixture
def metadata_dir():
    return METADATA_DIR


@pytest.fixture
def targets_dir():
    return TARGETS_DIR


@pytest.fixture
def root_history_dir():
    return ROOT_HISTORY_DIR


@pytest.fixture
def root_metadata():
    with open(METADATA_DIR / "root.json") as f:
        return json.load(f)


@pytest.fixture
def timestamp_metadata():
    with open(METADATA_DIR / "timestamp.json") as f:
        return json.load(f)


@pytest.fixture
def snapshot_metadata():
    with open(METADATA_DIR / "snapshot.json") as f:
        return json.load(f)


@pytest.fixture
def targets_metadata():
    with open(METADATA_DIR / "targets.json") as f:
        return json.load(f)


@pytest.fixture
def all_root_history():
    """Load all root history files in version order."""
    history = {}
    for path in ROOT_HISTORY_DIR.glob("*.root.json"):
        version = int(path.name.split(".")[0])
        with open(path) as f:
            history[version] = json.load(f)
    return dict(sorted(history.items()))
