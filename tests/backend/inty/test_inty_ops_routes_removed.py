from fastapi.routing import APIRoute

from backend.inty.main import app


def _route_paths() -> list[str]:
    return [
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
    ]


def test_inty_does_not_mount_evaluation_web_routes():
    route_paths = _route_paths()
    assert "/evaluation" not in route_paths
    assert "/evaluation/{path:path}" not in route_paths


def test_inty_does_not_include_ops_evaluation_api_routes():
    route_paths = _route_paths()
    assert not any(path.startswith("/api/v1/evaluation") for path in route_paths)
