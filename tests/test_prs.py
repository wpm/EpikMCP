"""Unit tests for prs.py."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from epik_gh.errors import ValidationError
from epik_gh.prs import (
    pr_close,
    pr_comment,
    pr_create,
    pr_edit,
    pr_get,
    pr_list,
    pr_merge,
    pr_review,
)

REPO = "owner/repo"


def _mock_run(return_value):
    return patch("epik_gh.prs.run_gh", return_value=(True, return_value, ""))


def test_pr_list_happy_path():
    items = [{"number": 1, "title": "Feature", "state": "open"}]
    with _mock_run(items):
        result = pr_list(REPO)
    assert result == items


def test_pr_list_invalid_state_raises_error():
    with pytest.raises(ValidationError, match="state"):
        pr_list(REPO, state="invalid")


def test_pr_list_passes_state():
    with patch("epik_gh.prs.run_gh", return_value=(True, [], "")) as mock:
        pr_list(REPO, state="closed")
    args = mock.call_args[0]
    assert "closed" in args


def test_pr_list_passes_base_filter():
    with patch("epik_gh.prs.run_gh", return_value=(True, [], "")) as mock:
        pr_list(REPO, base="main")
    args = mock.call_args[0]
    assert "--base" in args
    assert "main" in args


def test_pr_get_happy_path():
    pr = {"number": 10, "title": "My PR", "state": "open"}
    with _mock_run(pr):
        result = pr_get(REPO, 10)
    assert result == pr


def test_pr_create_happy_path():
    url = "https://github.com/owner/repo/pull/7"
    with _mock_run(url):
        result = pr_create(REPO, "My PR")
    assert result == {"url": url}


def test_pr_create_empty_title_raises_validation_error():
    with pytest.raises(ValidationError, match="title"):
        pr_create(REPO, "")


def test_pr_create_passes_draft_flag():
    with patch("epik_gh.prs.run_gh", return_value=(True, {}, "")) as mock:
        pr_create(REPO, "Draft PR", draft=True)
    args = mock.call_args[0]
    assert "--draft" in args


def test_pr_create_no_draft_flag_when_false():
    with patch("epik_gh.prs.run_gh", return_value=(True, {}, "")) as mock:
        pr_create(REPO, "Normal PR", draft=False)
    args = mock.call_args[0]
    assert "--draft" not in args


def test_pr_edit_happy_path():
    url = "https://github.com/owner/repo/pull/1"
    with _mock_run(url):
        result = pr_edit(REPO, 1, title="Updated PR")
    assert result == {"url": url}


def test_pr_close_happy_path():
    with _mock_run(""):
        result = pr_close(REPO, 2)
    assert result == {"number": 2, "state": "closed"}


def test_pr_merge_merge_method():
    with _mock_run(""):
        result = pr_merge(REPO, 5, method="merge")
    assert result == {"number": 5, "state": "merged"}


def test_pr_merge_squash_method():
    with _mock_run(""):
        result = pr_merge(REPO, 5, method="squash")
    assert result == {"number": 5, "state": "merged"}


def test_pr_merge_rebase_method():
    with _mock_run(""):
        result = pr_merge(REPO, 5, method="rebase")
    assert result == {"number": 5, "state": "merged"}


def test_pr_merge_invalid_method_raises_validation_error():
    with pytest.raises(ValidationError, match="method"):
        pr_merge(REPO, 5, method="fast-forward")


def test_pr_merge_passes_method_flag():
    with patch("epik_gh.prs.run_gh", return_value=(True, {}, "")) as mock:
        pr_merge(REPO, 5, method="squash")
    args = mock.call_args[0]
    assert "--squash" in args


def test_pr_merge_passes_delete_branch_flag():
    with patch("epik_gh.prs.run_gh", return_value=(True, {}, "")) as mock:
        pr_merge(REPO, 5, delete_branch=True)
    args = mock.call_args[0]
    assert "--delete-branch" in args


def test_pr_review_approve():
    with _mock_run(""):
        result = pr_review(REPO, 1, "approve")
    assert result["action"] == "approve"


def test_pr_review_comment_requires_body():
    with pytest.raises(ValidationError, match="body"):
        pr_review(REPO, 1, "comment", body="")


def test_pr_review_request_changes_requires_body():
    with pytest.raises(ValidationError, match="body"):
        pr_review(REPO, 1, "request-changes", body="")


def test_pr_review_invalid_action_raises_validation_error():
    with pytest.raises(ValidationError, match="action"):
        pr_review(REPO, 1, "invalid-action")


def test_pr_review_comment_with_body_succeeds():
    with _mock_run(""):
        result = pr_review(REPO, 1, "comment", body="Looks good")
    assert result["action"] == "comment"


def test_pr_comment_happy_path():
    url = "https://github.com/owner/repo/pull/1#issuecomment-1"
    with _mock_run(url):
        result = pr_comment(REPO, 1, "Nice work!")
    assert result == {"url": url}


def test_pr_comment_empty_body_raises_validation_error():
    with pytest.raises(ValidationError, match="body"):
        pr_comment(REPO, 1, "")
