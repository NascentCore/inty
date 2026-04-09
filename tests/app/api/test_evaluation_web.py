from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.evaluation_web import (
    API_ONLY_ENV_NAME,
    configure_evaluation_web_routes,
    is_api_only_mode_enabled,
)


def _prepare_static_dir(tmp_path: Path) -> str:
    evaluation_dir = tmp_path / "evaluation"
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    (evaluation_dir / "index.html").write_text("evaluation-home", encoding="utf-8")
    (evaluation_dir / "asset.txt").write_text("asset-content", encoding="utf-8")
    return str(tmp_path)


def test_is_api_only_mode_enabled_with_truthy_value(monkeypatch):
    monkeypatch.setenv(API_ONLY_ENV_NAME, "true")
    assert is_api_only_mode_enabled() is True


def test_is_api_only_mode_enabled_with_falsy_value(monkeypatch):
    monkeypatch.setenv(API_ONLY_ENV_NAME, "false")
    assert is_api_only_mode_enabled() is False


def test_configure_evaluation_web_routes_enabled(tmp_path):
    app = FastAPI()
    static_dir = _prepare_static_dir(tmp_path)

    configure_evaluation_web_routes(
        app=app,
        static_root_dir=static_dir,
        api_only_mode_enabled=False,
    )

    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "evaluation-home" in response.text

        legacy_response = client.get("/evaluation")
        assert legacy_response.status_code == 200
        assert "evaluation-home" in legacy_response.text

        legacy_slash = client.get("/evaluation/")
        assert legacy_slash.status_code == 200
        assert "evaluation-home" in legacy_slash.text

        static_file = client.get("/evaluation/asset.txt")
        assert static_file.status_code == 200
        assert static_file.text == "asset-content"

        static_mounted = client.get("/static/evaluation/index.html")
        assert static_mounted.status_code == 200


def test_configure_evaluation_web_routes_disabled_in_api_only_mode(tmp_path):
    app = FastAPI()
    static_dir = _prepare_static_dir(tmp_path)

    configure_evaluation_web_routes(
        app=app,
        static_root_dir=static_dir,
        api_only_mode_enabled=True,
    )

    with TestClient(app) as client:
        assert client.get("/").status_code == 404
        assert client.get("/evaluation").status_code == 404
        assert client.get("/evaluation/asset.txt").status_code == 404
        assert client.get("/static/evaluation/index.html").status_code == 404
