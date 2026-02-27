"""聊天/补全与业务提示词用业务动作（biz actions）。

**实验性。** 本模块为实验性模块，类型与 API 可能随时变更，不另行通知。
"""

from enum import StrEnum
from typing import List

from pydantic import BaseModel, Field

# 订阅弹窗用预留文案；在构建 SUBSCRIPTION_POPUP 类型 BizAction 时使用。
GENERAL_SUBSCRIPTION_POPUP_MESSAGES = (
    "Unlock unlimited chats with Premium.",
    "Get richer voices and priority replies with Premium.",
    "Keep talking with your favorite iMate - subscribe now.",
    "Upgrade to Premium for deeper conversations.",
)


class BizAction(BaseModel):
    """业务提示词用业务动作。"""

    class ActionType(StrEnum):
        # 什么也不做，作为占位符，某些场合用得上
        NONE = "none"
        # 显示订阅弹窗
        SUBSCRIPTION_POPUP = "subscription_popup"

    action_type: ActionType
    message: str = Field(..., description="展示给用户的消息")


ActionType = (
    BizAction.ActionType
)  # 便于调用方 from app.schemas.biz_action import ActionType


class BusinessActions(BaseModel):
    """一组业务动作的容器（如 subscription_actions）。"""

    subscription_actions: List[BizAction]
