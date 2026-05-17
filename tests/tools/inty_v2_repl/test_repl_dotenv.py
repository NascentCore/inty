"""Contract: REPL dotenv loads only ``tools/inty_v2_repl/.env``, not cwd ``.env``."""

from __future__ import annotations

import os

import tools.inty_v2_repl.repl_dotenv as repl_dotenv


def test_load_prototype_dotenv_ignores_cwd_dotenv(
    tmp_path,
    monkeypatch,
) -> None:
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / ".env").write_text(
        "INTY_V2_REPL_DOTENV_TEST_ONLY=from_pkg\n",
        encoding="utf-8",
    )
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / ".env").write_text(
        "INTY_V2_REPL_DOTENV_TEST_ONLY=from_cwd\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(cwd)
    monkeypatch.delenv("INTY_V2_REPL_DOTENV_TEST_ONLY", raising=False)
    monkeypatch.setattr(repl_dotenv, "_REPL_ENV_FILE", pkg_dir / ".env")
    repl_dotenv.load_prototype_dotenv()
    assert os.environ.get("INTY_V2_REPL_DOTENV_TEST_ONLY") == "from_pkg"
