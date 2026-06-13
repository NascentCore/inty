"""Create GitHub issues via REST API; retries alternate label sets on HTTP 422."""

from __future__ import annotations

from dataclasses import dataclass

import requests

_GITHUB_API_VERSION = "2022-11-28"
_GITHUB_ISSUES_TIMEOUT_SEC = 30.0


@dataclass(frozen=True)
class GithubIssueCreateInput:
    """Input for ``create_github_issue``."""

    repo: str
    token: str
    title: str
    body: str
    label_sets: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class GithubIssueCreateResult:
    """Created issue identifiers returned by GitHub."""

    url: str
    number: int


def _github_api_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": _GITHUB_API_VERSION,
    }


def create_github_issue(
    issue_input: GithubIssueCreateInput,
) -> GithubIssueCreateResult:
    """POST ``/repos/{owner}/{repo}/issues``; try each label set until one succeeds."""
    repo = issue_input.repo.strip()
    token = issue_input.token.strip()
    assert repo
    assert token
    assert issue_input.label_sets
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = _github_api_headers(token)
    payload_base = {
        "title": issue_input.title,
        "body": issue_input.body,
    }
    last_exc: Exception | None = None
    for labels in issue_input.label_sets:
        payload = {**payload_base, "labels": list(labels)}
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=_GITHUB_ISSUES_TIMEOUT_SEC,
        )
        if resp.status_code == 422:
            last_exc = requests.HTTPError(
                f"422 label set {labels!r}: {resp.text}",
                response=resp,
            )
            continue
        resp.raise_for_status()
        data = resp.json()
        issue_url = str(data.get("html_url") or "").strip()
        issue_number = int(data.get("number") or 0)
        assert issue_url
        assert issue_number > 0
        return GithubIssueCreateResult(url=issue_url, number=issue_number)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("create_github_issue: no label set attempted")
