import uuid
from typing import Iterable, List, Optional

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
        self._created_agents: List[str] = []

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
        assert response.status_code == 200, response.text
        self.token = response.json()["data"]["token"]
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})
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
        if response.status_code != 200:
            logger.warning(
                "Failed to delete user: status=%s, body=%s",
                response.status_code,
                response.text,
            )
            return

        # Try to clean up agents created during the test run
        for agent_id in list(self._created_agents):
            self.delete_agent(agent_id)
        self._created_agents.clear()

    def create_agent(
        self,
        *,
        name: Optional[str] = None,
        gender: str = "FEMALE",
        visibility: str = "PRIVATE",
        personality: str = "A caring and empathetic companion",
        scenario: str = "Acts as a supportive friend during testing",
    ) -> str:
        if not self.token:
            raise RuntimeError("call create_user() before creating agents")

        agent_name = name or f"Test Agent {uuid.uuid4().hex[:6]}"
        payload = {
            "name": agent_name,
            "gender": gender,
            "visibility": visibility,
            "personality": personality,
            "scenario": scenario,
            "intro": "Integration test agent",
            "opening": "Hi there, I'm here to help with testing!",
        }

        response = self.client.post(
            f"{self.base_url}/api/v1/ai/agents",
            json=payload,
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data.get("code") == 200, data

        agent_id = data["data"]["id"]
        self._created_agents.append(agent_id)
        return agent_id

    def delete_agent(self, agent_id: str) -> None:
        if not agent_id:
            return

        response = self.client.delete(
            f"{self.base_url}/api/v1/ai/agents/{agent_id}"
        )

        if response.status_code != 200:
            logger.warning(
                "Failed to delete agent: agent_id=%s status=%s body=%s",
                agent_id,
                response.status_code,
                response.text,
            )
            return

        data = response.json()
        if data.get("code") != 200:
            logger.warning(
                "Deleting agent returned non-success response: agent_id=%s body=%s",
                agent_id,
                data,
            )

        if agent_id in self._created_agents:
            self._created_agents.remove(agent_id)

    def chat_completions(
        self,
        agent_id: str,
        messages: Optional[Iterable[dict]] = None,
        *,
        language: str = "en",
    ) -> dict:
        if not self.token:
            raise RuntimeError(
                "call create_user() before requesting chat completions"
            )

        payload_messages = list(messages) if messages is not None else [
            {"role": "user", "content": "Hello, how are you?"}
        ]

        payload = {
            "messages": payload_messages,
            "stream": False,
            "model": "chatbot",
            "language": language,
        }

        response = self.client.post(
            f"{self.base_url}/api/v1/chat/completions/{agent_id}",
            json=payload,
        )

        assert response.status_code == 200, response.text
        return response.json()

    def text_to_image(self, text: str, count: int = 1) -> List[str]:
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

        assert response.status_code == 200, response.text
        response_data = response.json()

        code = response_data.get("code")
        if code != 200:
            error_msg = response_data.get("message", "Unknown error")
            raise RuntimeError(
                f"Image generation failed: code={code}, message={error_msg}, "
                f"data={response_data.get('data')}"
            )

        return response_data["data"]["urls"]

    def close(self):
        """Close the HTTP client."""
        self.client.close()
