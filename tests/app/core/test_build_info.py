import os

from app.core.build_info import build_time_utc, vcs_dirty, vcs_revision


def test_vcs_revision_empty_when_unset():
    for key in (
        "INTY_VCS_REVISION",
        "GITHUB_SHA",
        "SOURCE_VERSION",
        "COMMIT_SHA",
        "GIT_COMMIT",
    ):
        os.environ.pop(key, None)
    assert vcs_revision() == ""


def test_vcs_revision_prefers_inty_key():
    os.environ["INTY_VCS_REVISION"] = "aaa"
    os.environ["GITHUB_SHA"] = "bbb"
    try:
        assert vcs_revision() == "aaa"
    finally:
        os.environ.pop("INTY_VCS_REVISION", None)
        os.environ.pop("GITHUB_SHA", None)


def test_vcs_revision_falls_back_to_github_sha():
    os.environ.pop("INTY_VCS_REVISION", None)
    os.environ["GITHUB_SHA"] = "deadbeef"
    try:
        assert vcs_revision() == "deadbeef"
    finally:
        os.environ.pop("GITHUB_SHA", None)


def test_vcs_dirty_and_build_time():
    os.environ["INTY_VCS_DIRTY"] = "true"
    os.environ["INTY_BUILD_TIME"] = "2026-04-06T12:00:00Z"
    try:
        assert vcs_dirty() is True
        assert build_time_utc() == "2026-04-06T12:00:00Z"
    finally:
        os.environ.pop("INTY_VCS_DIRTY", None)
        os.environ.pop("INTY_BUILD_TIME", None)
