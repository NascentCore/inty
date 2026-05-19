"""
订阅权益功能常量定义
"""

from enum import Enum
from typing import Any, Dict, List


class FeatureType(str, Enum):
    """权益类型"""

    REAL = "real"  # 真实权益：实际提供功能
    FAKE = "fake"  # 虚假权益：仅用于前端展示


class SubscriptionFeatures:
    """订阅权益常量定义"""

    # 权益功能定义
    FEATURES = {
        "unlimited_messages": {
            "key": "unlimited_messages",
            "name": "聊天无限制",
            "description": "无限制聊天消息数量",
            "type": FeatureType.REAL,
            "icon": "💬",
            "order": 1,
        },
        "premium_model_usage": {
            "key": "premium_model_usage",
            "name": "高级模型使用",
            "description": "使用更先进的AI模型",
            "type": FeatureType.FAKE,
            "icon": "🧠",
            "order": 2,
        },
        "extra_chat_inspiration": {
            "key": "extra_chat_inspiration",
            "name": "更多聊天灵感",
            "description": "获得更多聊天话题建议",
            "type": FeatureType.FAKE,
            "icon": "💡",
            "order": 3,
        },
        "customize_ai_responses": {
            "key": "customize_ai_responses",
            "name": "自定义更好的ai回复",
            "description": "个性化AI回复风格",
            "type": FeatureType.FAKE,
            "icon": "🎨",
            "order": 4,
        },
        "chat_memory": {
            "key": "chat_memory",
            "name": "聊天记忆",
            "description": "AI记住聊天历史上下文",
            "type": FeatureType.FAKE,
            "icon": "🧠",
            "order": 5,
        },
        "new_features_privilege": {
            "key": "new_features_privilege",
            "name": "体验新功能特权",
            "description": "优先体验最新功能",
            "type": FeatureType.FAKE,
            "icon": "🚀",
            "order": 6,
        },
    }

    @classmethod
    def get_all_features(cls) -> Dict[str, Dict[str, Any]]:
        """获取所有权益功能"""
        return cls.FEATURES

    @classmethod
    def get_real_features(cls) -> Dict[str, Dict[str, Any]]:
        """获取真实权益功能"""
        return {
            k: v
            for k, v in cls.FEATURES.items()
            if v["type"] == FeatureType.REAL
        }

    @classmethod
    def get_fake_features(cls) -> Dict[str, Dict[str, Any]]:
        """获取虚假权益功能"""
        return {
            k: v
            for k, v in cls.FEATURES.items()
            if v["type"] == FeatureType.FAKE
        }

    @classmethod
    def get_feature_by_key(cls, key: str) -> Dict[str, Any]:
        """根据key获取权益功能"""
        return cls.FEATURES.get(key)

    @classmethod
    def is_real_feature(cls, feature_key: str) -> bool:
        """判断是否为真实权益"""
        feature = cls.get_feature_by_key(feature_key)
        return feature and feature["type"] == FeatureType.REAL

    @classmethod
    def get_premium_features_list(cls) -> List[Dict[str, Any]]:
        """获取Premium订阅的权益列表（按顺序）"""
        features = list(cls.FEATURES.values())
        return sorted(features, key=lambda x: x["order"])

    @classmethod
    def get_premium_features_dict(cls) -> Dict[str, Any]:
        """获取Premium订阅的权益字典格式"""
        return {
            "features": cls.get_premium_features_list(),
            "real_features": list(cls.get_real_features().keys()),
            "fake_features": list(cls.get_fake_features().keys()),
        }
