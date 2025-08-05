"""
订阅权限相关的统一错误码定义
"""

from typing import Dict, Any, Optional, TypeVar
from app.schemas.response import APIResponse

T = TypeVar("T")


class SubscriptionError:
    """订阅权限错误码类"""

    # 错误码常量
    STYLE_PROMPT_SUBSCRIPTION_REQUIRED = "STYLE_PROMPT_SUBSCRIPTION_REQUIRED"
    CHAT_LIMIT_EXCEEDED = "CHAT_LIMIT_EXCEEDED"
    BACKGROUND_GENERATION_LIMIT_EXCEEDED = "BACKGROUND_GENERATION_LIMIT_EXCEEDED"
    AGENT_CREATION_LIMIT_EXCEEDED = "AGENT_CREATION_LIMIT_EXCEEDED"

    # 错误码配置
    ERROR_CONFIGS = {
        STYLE_PROMPT_SUBSCRIPTION_REQUIRED: {
            "code": 403,
            "message": "Style prompt feature requires subscription",
            "description": "Style prompt feature requires subscription",
        },
        CHAT_LIMIT_EXCEEDED: {
            "code": 403,
            "message": "Daily chat limit exceeded",
            "description": "Daily chat limit exceeded",
        },
        BACKGROUND_GENERATION_LIMIT_EXCEEDED: {
            "code": 403,
            "message": "Background image generation limit exceeded",
            "description": "Background image generation limit exceeded",
        },
        AGENT_CREATION_LIMIT_EXCEEDED: {
            "code": 403,
            "message": "Agent creation limit exceeded",
            "description": "Agent creation limit exceeded",
        },
    }

    @classmethod
    def create_error_response(
        cls, error_code: str, extra_data: Dict[str, Any] = None
    ) -> APIResponse[Dict[str, Any]]:
        """
        创建统一格式的订阅权限错误响应

        Args:
            error_code: 错误码
            extra_data: 额外数据（如使用次数、限制次数等）

        Returns:
            APIResponse
        """
        if error_code not in cls.ERROR_CONFIGS:
            raise ValueError(f"Unknown error code: {error_code}")

        config = cls.ERROR_CONFIGS[error_code]

        # 构建错误数据
        error_data = {
            "error_code": error_code,
            "description": config["description"],
        }

        # 添加额外数据
        if extra_data:
            error_data.update(extra_data)

        return APIResponse.error(
            message=config["message"], code=config["code"], data=error_data
        )

    @classmethod
    def get_error_config(cls, error_code: str) -> Dict[str, Any]:
        """获取错误码配置"""
        return cls.ERROR_CONFIGS.get(error_code, {})

    @classmethod
    def is_subscription_error(cls, error_code: str) -> bool:
        """检查是否为订阅权限相关错误"""
        return error_code in cls.ERROR_CONFIGS


# 便捷方法
def create_style_prompt_subscription_required_response() -> APIResponse[Dict[str, Any]]:
    """创建设置风格提示词需要订阅的错误响应"""
    return SubscriptionError.create_error_response(
        SubscriptionError.STYLE_PROMPT_SUBSCRIPTION_REQUIRED
    )


def create_chat_limit_exceeded_response(
    used_count: int, daily_limit: int
) -> APIResponse[Dict[str, Any]]:
    """创建聊天次数限制错误响应"""
    return SubscriptionError.create_error_response(
        SubscriptionError.CHAT_LIMIT_EXCEEDED,
        {"used_count": used_count, "daily_limit": daily_limit},
    )


def create_background_generation_limit_exceeded_response(
    used_count: int, limit: int, is_subscribed: bool = False
) -> APIResponse[Dict[str, Any]]:
    """创建背景图生成限制错误响应"""
    # 根据订阅状态显示不同消息
    message = (
        "Daily background image generation limit exceeded"
        if is_subscribed
        else "Daily free background image generation limit exceeded"
    )

    return SubscriptionError.create_error_response(
        SubscriptionError.BACKGROUND_GENERATION_LIMIT_EXCEEDED,
        {
            "used_count": used_count,
            "limit": limit,
            "is_subscribed": is_subscribed,
            "detailed_message": message,
        },
    )


def create_agent_creation_limit_exceeded_response(
    used_count: int, limit: int
) -> APIResponse[Dict[str, Any]]:
    """创建Agent创建限制错误响应"""
    return SubscriptionError.create_error_response(
        SubscriptionError.AGENT_CREATION_LIMIT_EXCEEDED,
        {"used_count": used_count, "limit": limit},
    )
