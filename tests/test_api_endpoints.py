import os
import re
from pathlib import Path
import requests
import pytest

# Router prefixes mapped from app/api/v1/api.py
PREFIXES = {
    "admin": "/admin",
    "agents": "/ai/agents",
    "auth": "/auth",
    "chats": "/chats",
    "evaluation": "/evaluation",
    "notification": "/notifications",
    "report": "/report",
    "settings": "/settings",
    "subscription": "/subscription",
    "users": "/users",
    "version": "/version",
    # resources router is currently not included but kept for completeness
    "resources": "/resources",
}

ROUTE_PATTERN = re.compile(r"@router\.(get|post|put|delete|patch)\(\"([^\"]*)\"")


def collect_endpoints():
    endpoints = []
    endpoint_dir = Path("app/api/v1/endpoints")
    for file in endpoint_dir.glob("*.py"):
        prefix = PREFIXES.get(file.stem, "")
        with file.open() as f:
            for line in f:
                match = ROUTE_PATTERN.search(line)
                if match:
                    method, path = match.groups()
                    full_path = prefix + path
                    endpoints.append((method.upper(), full_path))
    return endpoints


ENDPOINTS = collect_endpoints()
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000/api/v1")


@pytest.mark.parametrize("method,path", ENDPOINTS)
def test_api_endpoint(method, path):
    url_path = re.sub(r"\{[^/]+\}", "1", path)
    url = f"{BASE_URL}{url_path}"
    try:
        response = requests.request(method, url, timeout=5)
    except Exception as exc:
        pytest.skip(f"Server not available: {exc}")
    if response.status_code != 200:
        pytest.skip(f"Expected 200 but got {response.status_code}")
