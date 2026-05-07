"""Unit tests for relationships.py."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from epik_gh.errors import ValidationError
from epik_gh.relationships import (
    issue_add_sub_issue,
    issue_list_relationships,
    issue_remove_blocked_by,
    issue_remove_sub_issue,
    issue_set_blocked_by,
)

REPO = "owner/repo"


def _node_id_raw(node_id: str) -> str:
    return json.dumps({"data": {"repository": {"issue": {"id": node_id}}}})


def test_issue_set_blocked_by_happy_path():
    mutation_response = json.dumps(
        {
            "data": {
                "addIssueRelationship": {"issueRelationship": {"type": "BLOCKED_BY"}}
            }
        }
    )
    side_effects = [
        (True, _node_id_raw("issue_id_1"), ""),
        (True, _node_id_raw("issue_id_2"), ""),
        (True, mutation_response, ""),
    ]
    with patch("epik_gh.relationships.run_gh", side_effect=side_effects):
        result = issue_set_blocked_by(REPO, 1, 2)

    assert result["issue"] == 1
    assert result["blocked_by"] == 2
    assert result["relationship"] == "blocked_by"


def test_issue_set_blocked_by_cross_repo():
    other_repo = "other/repo"
    mutation_response = json.dumps(
        {
            "data": {
                "addIssueRelationship": {"issueRelationship": {"type": "BLOCKED_BY"}}
            }
        }
    )
    side_effects = [
        (True, _node_id_raw("issue_id_1"), ""),
        (True, _node_id_raw("issue_id_2"), ""),
        (True, mutation_response, ""),
    ]
    with patch("epik_gh.relationships.run_gh", side_effect=side_effects) as mock:
        result = issue_set_blocked_by(REPO, 1, 2, blocked_by_repo=other_repo)

    assert result["blocked_by_repo"] == other_repo
    # Second node-id lookup must pass other_repo's owner, not REPO's owner
    second_call_args = mock.call_args_list[1][0]
    assert "owner=other" in " ".join(second_call_args)


def test_issue_set_blocked_by_passes_variables_as_flags():
    """Variables must be passed as individual -F/-f flags, not as a JSON blob."""
    side_effects = [
        (True, _node_id_raw("issue_id_1"), ""),
        (True, _node_id_raw("issue_id_2"), ""),
        (
            True,
            json.dumps(
                {
                    "data": {
                        "addIssueRelationship": {
                            "issueRelationship": {"type": "BLOCKED_BY"}
                        }
                    }
                }
            ),
            "",
        ),
    ]
    with patch("epik_gh.relationships.run_gh", side_effect=side_effects) as mock:
        issue_set_blocked_by(REPO, 1, 2)

    first_call_args = mock.call_args_list[0][0]
    # Should NOT contain a variables= blob
    assert not any("variables=" in a for a in first_call_args)
    # Should contain individual owner= and name= flags
    assert any("owner=owner" in a for a in first_call_args)
    assert any("name=repo" in a for a in first_call_args)


def test_issue_set_blocked_by_invalid_repo_format():
    with (
        pytest.raises(ValidationError, match="owner/name"),
        patch("epik_gh.relationships.run_gh", return_value=(True, "{}", "")),
    ):
        issue_set_blocked_by("badrepo", 1, 2)


def test_issue_remove_blocked_by_happy_path():
    mutation_response = json.dumps(
        {"data": {"removeIssueRelationship": {"clientMutationId": None}}}
    )
    side_effects = [
        (True, _node_id_raw("issue_id_1"), ""),
        (True, _node_id_raw("issue_id_2"), ""),
        (True, mutation_response, ""),
    ]
    with patch("epik_gh.relationships.run_gh", side_effect=side_effects):
        result = issue_remove_blocked_by(REPO, 1, 2)

    assert result["issue"] == 1
    assert result["removed_blocked_by"] == 2


def test_issue_remove_blocked_by_cross_repo():
    other_repo = "other/repo"
    mutation_response = json.dumps(
        {"data": {"removeIssueRelationship": {"clientMutationId": None}}}
    )
    side_effects = [
        (True, _node_id_raw("issue_id_1"), ""),
        (True, _node_id_raw("issue_id_2"), ""),
        (True, mutation_response, ""),
    ]
    with patch("epik_gh.relationships.run_gh", side_effect=side_effects) as mock:
        result = issue_remove_blocked_by(REPO, 1, 2, blocked_by_repo=other_repo)

    assert result["blocked_by_repo"] == other_repo
    second_call_args = mock.call_args_list[1][0]
    assert "owner=other" in " ".join(second_call_args)


def test_issue_list_relationships_happy_path():
    gql_data = json.dumps(
        {
            "data": {
                "repository": {
                    "issue": {
                        "trackedInIssues": {
                            "nodes": [
                                {
                                    "number": 5,
                                    "title": "Parent",
                                    "url": "https://...",
                                }
                            ]
                        },
                        "trackedIssues": {"nodes": []},
                    }
                }
            }
        }
    )
    with patch("epik_gh.relationships.run_gh", return_value=(True, gql_data, "")):
        result = issue_list_relationships(REPO, 1)

    assert result["issue_number"] == 1
    assert len(result["tracked_in"]) == 1
    assert result["tracked_in"][0]["number"] == 5


def test_issue_list_relationships_passes_variables_as_flags():
    gql_data = json.dumps(
        {
            "data": {
                "repository": {
                    "issue": {
                        "trackedInIssues": {"nodes": []},
                        "trackedIssues": {"nodes": []},
                    }
                }
            }
        }
    )
    with patch(
        "epik_gh.relationships.run_gh", return_value=(True, gql_data, "")
    ) as mock:
        issue_list_relationships(REPO, 42)

    args = mock.call_args[0]
    assert not any("variables=" in a for a in args)
    assert any("owner=owner" in a for a in args)
    assert any("name=repo" in a for a in args)
    assert any("number=42" in a for a in args)


def test_issue_add_sub_issue_happy_path():
    mutation_response = json.dumps(
        {
            "data": {
                "addSubIssue": {
                    "issue": {"number": 10},
                    "subIssue": {"number": 20},
                }
            }
        }
    )
    side_effects = [
        (True, _node_id_raw("parent_id"), ""),
        (True, _node_id_raw("sub_id"), ""),
        (True, mutation_response, ""),
    ]
    with patch("epik_gh.relationships.run_gh", side_effect=side_effects):
        result = issue_add_sub_issue(REPO, 10, 20)

    assert result["parent"] == 10
    assert result["sub_issue"] == 20


def test_issue_remove_sub_issue_happy_path():
    mutation_response = json.dumps(
        {
            "data": {
                "removeSubIssue": {
                    "issue": {"number": 10},
                    "subIssue": {"number": 20},
                }
            }
        }
    )
    side_effects = [
        (True, _node_id_raw("parent_id"), ""),
        (True, _node_id_raw("sub_id"), ""),
        (True, mutation_response, ""),
    ]
    with patch("epik_gh.relationships.run_gh", side_effect=side_effects):
        result = issue_remove_sub_issue(REPO, 10, 20)

    assert result["parent"] == 10
    assert result["removed_sub_issue"] == 20
