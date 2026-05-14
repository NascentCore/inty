from tests.app.api.test_client import TestClient


def _assert_telegram_metadata(agent_payload: dict, agent_id: str) -> dict:
    telegram = (agent_payload.get("extensions") or {}).get("telegram")
    assert isinstance(telegram, dict), (
        f"expected telegram extension metadata for promoted agent {agent_id}: "
        f"{agent_payload}"
    )
    expected = {
        "status": "provisioned",
        "start_parameter": f"agent_{agent_id}",
        "bot_username": "inty_test_bot",
        "deep_link": f"https://t.me/inty_test_bot?start=agent_{agent_id}",
    }
    for key, expected_value in expected.items():
        assert telegram.get(key) == expected_value, (
            f"unexpected telegram {key} for promoted agent {agent_id}: " f"{telegram}"
        )
    return telegram


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

        telegram = _assert_telegram_metadata(promoted_agent, agent_id)

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
