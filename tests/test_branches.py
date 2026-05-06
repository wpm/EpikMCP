"""Unit tests for branches.py."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from epik_gh.branches import branch_create, branch_delete, branch_list
from epik_gh.errors import ValidationError

REPO = "owner/repo"


def _mock_run(return_value):
    return patch("epik_gh.branches.run_gh", return_value=(True, return_value, ""))


def test_branch_list_happy_path():
    api_response = json.dumps(
        [
            {"name": "main", "commit": {"sha": "abc123"}},
            {"name": "dev", "commit": {"sha": "def456"}},
        ]
    )
    with _mock_run(api_response):
        result = branch_list(REPO)
    assert len(result) == 2
    assert result[0] == {"name": "main", "sha": "abc123"}


def test_branch_list_prefix_filter():
    api_response = json.dumps(
        [
            {"name": "feature/foo", "commit": {"sha": "aaa"}},
            {"name": "main", "commit": {"sha": "bbb"}},
            {"name": "feature/bar", "commit": {"sha": "ccc"}},
        ]
    )
    with _mock_run(api_response):
        result = branch_list(REPO, prefix="feature/")
    assert len(result) == 2
    assert all(b["name"].startswith("feature/") for b in result)


def test_branch_list_invalid_repo_format_raises_validation_error():
    with pytest.raises(ValidationError, match="owner/name"):
        branch_list("just-a-name")


def test_branch_create_happy_path():
    sha = "abc123def456" * 3 + "abcd"  # 40 chars
    resolve_response = {"sha": sha}
    create_response = json.dumps({"ref": "refs/heads/new-branch", "sha": sha})

    side_effects = [
        (True, resolve_response, ""),  # _resolve_ref call
        (True, create_response, ""),  # POST to create ref
    ]

    with patch("epik_gh.branches.run_gh", side_effect=side_effects):
        result = branch_create(REPO, "new-branch", "main")

    assert result["branch"] == "new-branch"
    assert result["sha"] == sha


def test_branch_create_empty_branch_name_raises_validation_error():
    with pytest.raises(ValidationError, match="branch_name"):
        branch_create(REPO, "", "main")


def test_branch_create_empty_ref_raises_validation_error():
    with pytest.raises(ValidationError, match="ref"):
        branch_create(REPO, "new-branch", "")


def test_branch_delete_happy_path():
    with _mock_run(""):
        result = branch_delete(REPO, "old-branch", force=True)
    assert result["deleted"] == "old-branch"
    assert result["repo"] == REPO


def test_branch_delete_force_false_raises_validation_error():
    with pytest.raises(ValidationError, match="force"):
        branch_delete(REPO, "old-branch", force=False)


def test_branch_delete_default_force_raises_validation_error():
    with pytest.raises(ValidationError, match="force"):
        branch_delete(REPO, "old-branch")
