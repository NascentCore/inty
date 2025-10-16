import uuid

import httpx


class TestClient:
    """
    A minimal client for testing Inty APIs.

    It's not auto-generated from OpenAPI spec, but hand rolled, as we do not need
    complex features.

    These api will use the same internal data structure for convenience,
    but access Inty backend API through HTTP interface.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.device_id = f"test-device-{uuid.uuid4().hex[:8]}"
        self.client = httpx.Client(timeout=30.0)
        self.token = None
        self.guest_id = None

    def create_user(self) -> str:
        """Create a guest user and return the token."""
        response = self.client.post(
            f"{self.base_url}/api/v1/auth/guest",
            json={
                "device_id": self.device_id,
                "system_language": "en",
                "age_group": "adult",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

        self.token = data["data"]["token"]
        self.guest_id = data["data"]["guest_id"]
        return self.token

    def delete_user(self) -> None:
        """Delete the user account."""
        if not self.token:
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        response = self.client.post(
            f"{self.base_url}/api/v1/users/delete-account",
            headers=headers,
        )
        assert response.status_code == 200

    def close(self):
        """Close the HTTP client."""
        self.client.close()
