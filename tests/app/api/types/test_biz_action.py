# Unit tests for app.api.types.biz_action (BizAction, BusinessActions, ActionType, constant)

import pytest

from app.api.types.biz_action import (
    GENERAL_SUBSCRIPTION_POPUP_MESSAGES,
    ActionType,
    BizAction,
    BusinessActions,
)


def test_action_type_values():
    assert ActionType.NONE == "none"
    assert ActionType.SUBSCRIPTION_POPUP == "subscription_popup"


def test_biz_action_serialization():
    action = BizAction(action_type=ActionType.NONE, message="")
    dumped = action.model_dump()
    assert dumped["action_type"] == "none"
    assert dumped["message"] == ""


def test_biz_action_subscription_popup_roundtrip():
    action = BizAction(
        action_type=ActionType.SUBSCRIPTION_POPUP,
        message="Unlock unlimited chats with Premium.",
    )
    dumped = action.model_dump()
    assert dumped["action_type"] == "subscription_popup"
    assert dumped["message"] == "Unlock unlimited chats with Premium."
    restored = BizAction.model_validate(dumped)
    assert restored.action_type == action.action_type
    assert restored.message == action.message


def test_business_actions_serialization():
    actions = BusinessActions(
        subscription_actions=[
            BizAction(action_type=ActionType.NONE, message=""),
        ]
    )
    dumped = actions.model_dump()
    assert "subscription_actions" in dumped
    assert len(dumped["subscription_actions"]) == 1
    assert dumped["subscription_actions"][0]["action_type"] == "none"


def test_business_actions_empty_list_valid():
    actions = BusinessActions(subscription_actions=[])
    assert actions.subscription_actions == []


def test_general_subscription_popup_messages_non_empty():
    assert len(GENERAL_SUBSCRIPTION_POPUP_MESSAGES) > 0
    for msg in GENERAL_SUBSCRIPTION_POPUP_MESSAGES:
        assert isinstance(msg, str)
        assert len(msg.strip()) > 0
