"""Tests for `tools/scripts/init_admin_user.py` DB session lifecycle."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from tools.scripts import init_admin_user


def test_create_user_closes_db_session_on_reused_token_early_return(
    tmp_path: Path,
) -> None:
    """`create_user` must close the DB session it opens even when it returns
    early because an existing bearer token in `--token-file` is still usable."""
    token_file = tmp_path / "token.txt"
    token_file.write_text("existing-token\n", encoding="utf-8")

    mock_db = MagicMock()
    mock_user = MagicMock(
        id=init_admin_user.DEFAULT_ADMIN_USER_ID, is_superuser=True
    )
    mock_db.query.return_value.filter.return_value.first.return_value = (
        mock_user
    )

    with (
        patch.object(init_admin_user, "SessionLocal", return_value=mock_db),
        patch.object(
            init_admin_user, "existing_bearer_token_usable", return_value=True
        ),
    ):
        init_admin_user.create_user(token_file=token_file)

    mock_db.close.assert_called_once()


def test_create_user_closes_db_session_on_normal_completion(
    tmp_path: Path,
) -> None:
    """`create_user` must also close the DB session on the non-early-return path."""
    mock_db = MagicMock()
    mock_user = MagicMock(
        id=init_admin_user.DEFAULT_ADMIN_USER_ID, is_superuser=True
    )
    mock_db.query.return_value.filter.return_value.first.return_value = (
        mock_user
    )

    with (
        patch.object(init_admin_user, "SessionLocal", return_value=mock_db),
        patch.object(
            init_admin_user, "create_access_token", return_value="new-token"
        ),
    ):
        init_admin_user.create_user(token_file=None)

    mock_db.close.assert_called_once()
