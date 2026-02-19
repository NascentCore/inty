from enum import StrEnum
from typing import List

from pydantic import BaseModel, Field

# Reserved copy for subscription_popup actions; use when building SUBSCRIPTION_POPUP BizAction.
GENERAL_SUBSCRIPTION_POPUP_MESSAGES = (
    "Unlock unlimited chats with Premium.",
    "Get richer voices and priority replies with Premium.",
    "Keep talking with your favorite iMate - subscribe now.",
    "Upgrade to Premium for deeper conversations.",
)


class BizAction(BaseModel):
    """Business actions for business prompts."""

    class ActionType(StrEnum):
        # 什么也不做，作为占位符，某些场合用得上
        NONE = "none"
        # 显示订阅弹窗
        SUBSCRIPTION_POPUP = "subscription_popup"

    action_type: ActionType
    message: str = Field(..., description="The message to display to the user")


ActionType = BizAction.ActionType  # 便于调用方 from app.api.types.biz_action import ActionType


class BusinessActions(BaseModel):
    """Container for a list of biz actions (e.g. subscription_actions)."""

    subscription_actions: List[BizAction]
