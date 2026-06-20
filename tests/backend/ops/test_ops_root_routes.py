from fastapi.routing import APIRoute

from backend.ops.main import app


def _ops_route_paths() -> list[str]:
    return [route.path for route in app.routes if isinstance(route, APIRoute)]


def test_ops_mounts_evaluation_page_on_root_and_keeps_health_endpoint():
    route_paths = _ops_route_paths()
    assert route_paths.count("/") == 1
    assert "/health" in route_paths
    assert "/evaluation" in route_paths
