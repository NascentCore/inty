from tests.app.api.test_client import TestClient


def test_promote_private_agent_to_public_provisions_telegram_metadata(
    integration_client: TestClient,
):
    agent_id = integration_client.create_agent(
        name="Telegram Provision E2E Agent",
        visibility="PRIVATE",
    )

    try:
        promote_response = integration_client.client.put(
            f"{integration_client.base_url}/api/v1/ai/agents/{agent_id}",
            json={"visibility": "PUBLIC"},
        )
        assert promote_response.status_code == 200, promote_response.text
        promoted_agent = promote_response.json()

        telegram = (promoted_agent.get("extensions") or {}).get("telegram")
        assert isinstance(telegram, dict), promoted_agent
        assert telegram.get("status") == "provisioned", promoted_agent
        assert telegram.get("start_parameter") == f"agent_{agent_id}", promoted_agent
        assert telegram.get("bot_username") == "inty_test_bot", promoted_agent
        assert telegram.get("deep_link") == (
            f"https://t.me/inty_test_bot?start=agent_{agent_id}"
        ), promoted_agent

        second_update_response = integration_client.client.put(
            f"{integration_client.base_url}/api/v1/ai/agents/{agent_id}",
            json={"intro": "public-ready"},
        )
        assert second_update_response.status_code == 200, second_update_response.text
        second_updated_agent = second_update_response.json()
        telegram_after_second_update = (
            second_updated_agent.get("extensions") or {}
        ).get("telegram")
        assert telegram_after_second_update == telegram, second_updated_agent
    finally:
        integration_client.delete_agent(agent_id)
