# CREATED_BY_AGENT

from fastapi.routing import APIRoute

from app.api import deps
from backend.ops.api.v1 import evaluation


def _get_user_analytics_routes() -> list[APIRoute]:
    return [
        route
        for route in evaluation.router.routes
        if isinstance(route, APIRoute) and "/user-analytics/" in route.path
    ]


def test_user_analytics_routes_use_replica_db_dependency() -> None:
    routes = _get_user_analytics_routes()
    assert routes, "No /user-analytics/ routes found in evaluation router"

    for route in routes:
        dependency_calls = {
            dependency.call
            for dependency in route.dependant.dependencies
            if dependency.call is not None
        }
        assert (
            deps.get_async_replica_db in dependency_calls
        ), f"{route.path} should use get_async_replica_db"
        assert (
            deps.get_async_db not in dependency_calls
        ), f"{route.path} should not use get_async_db"
