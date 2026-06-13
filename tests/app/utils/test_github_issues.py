"""Tests for app.utils.github.issues."""

from __future__ import annotations

import pytest

from app.utils.github.issues import GithubIssueCreateInput, create_github_issue


def test_create_github_issue_requires_label_sets() -> None:
    with pytest.raises(AssertionError):
        create_github_issue(
            GithubIssueCreateInput(
                repo="nascentcore/inty",
                token="t",
                title="t",
                body="b",
                label_sets=(),
            )
        )
