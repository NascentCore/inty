"""Unit tests for ``scripts/list_inty_ops_agents_admin.py`` (mocked HTTP)."""

from __future__ import annotations

import importlib.util
import json
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from urllib.error import HTTPError

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "list_inty_ops_agents_admin.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "list_inty_ops_agents_admin", _SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def list_mod():
    return _load_script_module()


@pytest.fixture
def token_file(tmp_path):
    p = tmp_path / "tok.txt"
    p.write_text("fake-bearer-token\n", encoding="utf-8")
    return str(p)


def test_run_list_two_agents(list_mod, token_file):
    payload = {
        "code": 200,
        "data": [
            {"id": "11111111-1111-1111-1111-111111111111", "name": "A"},
            {"id": "22222222-2222-2222-2222-222222222222", "name": "B"},
        ],
    }

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    out, err = StringIO(), StringIO()
    with patch.object(list_mod.urllib.request, "urlopen", return_value=FakeResp()):
        rc = list_mod.run_list(
            api_base="http://127.0.0.1:8001",
            token_path=token_file,
            limit=50,
            timeout=60.0,
            stdout=out,
            stderr=err,
        )
    assert rc == 0
    assert err.getvalue() == ""
    lines = out.getvalue().strip().splitlines()
    assert lines == [
        "11111111-1111-1111-1111-111111111111\tA",
        "22222222-2222-2222-2222-222222222222\tB",
    ]


def test_run_list_empty_data_guidance(list_mod, token_file):
    payload = {"code": 200, "data": []}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    out, err = StringIO(), StringIO()
    with patch.object(list_mod.urllib.request, "urlopen", return_value=FakeResp()):
        rc = list_mod.run_list(
            api_base="http://127.0.0.1:8001",
            token_path=token_file,
            limit=50,
            timeout=60.0,
            stdout=out,
            stderr=err,
        )
    assert rc == 0
    assert err.getvalue() == ""
    assert "admin/list returned no agents" in out.getvalue()
    assert "test_chat_ws.py" in out.getvalue()
    assert "--create-agent" in out.getvalue()


def test_run_list_http_error(list_mod, token_file):
    fp = BytesIO(b'{"detail":"forbidden"}')
    err_http = HTTPError(
        "http://127.0.0.1:8001/api/v1/ai/agents/admin/list",
        403,
        "Forbidden",
        hdrs=None,
        fp=fp,
    )

    out, err = StringIO(), StringIO()
    with patch.object(
        list_mod.urllib.request, "urlopen", side_effect=err_http
    ):
        rc = list_mod.run_list(
            api_base="http://127.0.0.1:8001",
            token_path=token_file,
            limit=50,
            timeout=60.0,
            stdout=out,
            stderr=err,
        )
    assert rc == 1
    assert out.getvalue() == ""
    assert "HTTP 403" in err.getvalue()


def test_run_list_api_body_code_not_200(list_mod, token_file):
    payload = {"code": 403, "message": "Not superuser"}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    out, err = StringIO(), StringIO()
    with patch.object(list_mod.urllib.request, "urlopen", return_value=FakeResp()):
        rc = list_mod.run_list(
            api_base="http://127.0.0.1:8001",
            token_path=token_file,
            limit=50,
            timeout=60.0,
            stdout=out,
            stderr=err,
        )
    assert rc == 1
    assert out.getvalue() == ""
    assert "API error code=403" in err.getvalue()
    assert "Not superuser" in err.getvalue()
