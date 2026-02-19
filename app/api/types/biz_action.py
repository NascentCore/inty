from typing import List

from pydantic import BaseModel, Field

GENERAL_SUBSCRIPTION_POPUP_MESSAGES = (
    "Unlock unlimited chats with Premium.",
    "Get richer voices and priority replies with Premium.",
    "Keep talking with your favorite iMate - subscribe now.",
    "Upgrade to Premium for deeper conversations.",
)


class BizAction(BaseModel):
    """General business actions for growth and subscription prompts."""

    # AI 工作总结：
    # 1) 将通用订阅弹窗文案集中为一个后端类型，避免分散在不同 endpoint。
    # 2) 用标准字段 business_actions 统一向 Android 客户端透出文案列表。
    business_actions: List[str] = Field(
        default_factory=lambda: list(GENERAL_SUBSCRIPTION_POPUP_MESSAGES),
        min_length=1,
        description=(
            "General short messages for subscription popup prompts when users chat with AI "
            "characters."
        ),
    )
