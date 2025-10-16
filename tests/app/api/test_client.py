import uuid

import httpx
from loguru import logger


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
        self.client = httpx.Client(timeout=30.0)
        self.token = None
        self.device_id = None

    def create_user(self) -> str:
        """Create a guest user and return the token."""
        if not self.device_id:
            self.device_id = f"test-device-{uuid.uuid4().hex[:8]}"
        response = self.client.post(
            f"{self.base_url}/api/v1/auth/guest",
            json={
                "device_id": self.device_id,
                "system_language": "en",
                "age_group": "adult",
            },
        )
        assert response.status_code == 200
        self.token = response.json()["data"]["token"]
        self.client.headers = {"Authorization": f"Bearer {self.token}"}
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

    def text_to_image(self, text: str, count: int = 4) -> list[str]:
        url = f"{self.base_url}/api/v1/ai/agents/text-to-image"
        payload = {"prompt": text, "count": count}
        headers = self.client.headers.copy()

        logger.debug(f"Making POST request to: {url}")
        logger.debug(f"Headers: {headers}")
        logger.debug(f"Payload: {payload}")

        response = self.client.post(url, json=payload)

        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")
        logger.debug(f"Response body: {response.text}")

        assert response.status_code == 200
        response_data = response.json()

        return response_data["data"]["image_uris"]

    def close(self):
        """Close the HTTP client."""
        self.client.close()
