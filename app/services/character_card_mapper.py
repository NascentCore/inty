import re
import uuid
from typing import Any, Dict, List, Optional

from loguru import logger

from app.models.agent import AgentStatus, AgentVisibility
from app.models.user import Gender
from app.schemas.character_card import CharacterCardDataV2, CharacterCardV2


class CharacterCardMapper:
    """角色卡映射服务"""

    def __init__(self):
        self.gender_keywords = {
            "male": [
                "man",
                "boy",
                "male",
                "he",
                "him",
                "his",
                "gentleman",
                "guy",
                "dude",
            ],
            "female": ["woman", "girl", "female", "she", "her", "hers", "lady", "gal"],
            "other": ["non-binary", "they", "them", "their", "enby", "genderfluid"],
        }

    def map_card_to_agent(
        self, card_data: CharacterCardV2, user_id: str
    ) -> Dict[str, Any]:
        """
        将角色卡数据映射到Agent字段

        Args:
            card_data: 角色卡数据
            user_id: 用户ID

        Returns:
            Agent创建数据字典
        """
        data = card_data.data
# 生成Agent ID
        agent_id = str(uuid.uuid4())
# 构建基础代理数据
        agent_data = {
            "id": agent_id,
            "name": data.name[:30],  # 限制名称长度
            "gender": self._infer_gender(data),
            "intro": data.description,
            "opening": (
                data.first_mes or data.alternate_greetings[0]
                if data.alternate_greetings
                else ""
            ),
            "prompt": self._build_system_prompt(data),
            "visibility": AgentVisibility.PRIVATE,  # 导入的角色卡默认为私有
            "status": AgentStatus.PENDING,
            "creator_id": user_id,
            "category": self._extract_category_from_tags(data.tags),
# 角色卡特定字段
            "character_card_spec": card_data.spec.value,
            "character_card_data": card_data.dict(),
            "personality": data.personality,
            "scenario": data.scenario,
            "first_message": data.first_mes,
            "message_example": data.mes_example,
            "creator_notes": data.creator_notes,
            "post_history_instructions": data.post_history_instructions,
            "alternate_greetings": data.alternate_greetings,
            "character_book": (
                data.character_book.dict() if data.character_book else None
            ),
            "tags": data.tags,
            "character_version": data.character_version,
            "extensions": data.extensions,
        }

        logger.debug(f"成功映射角色卡到Agent数据: {data.name}")
        return agent_data

    def map_agent_to_card(self, agent_data: Dict[str, Any]) -> CharacterCardV2:
        """
        将Agent数据映射到角色卡格式

        Args:
            agent_data: Agent数据字典

        Returns:
            角色卡数据
        """
# 如果Agent有原始角色卡数据，优先使用
        if agent_data.get("character_card_data"):
            try:
                return CharacterCardV2(**agent_data["character_card_data"])
            except Exception as e:
                logger.warning(f"解析原始角色卡数据失败: {e}")
# 从Agent字段构建角色卡数据
        card_data = CharacterCardDataV2(
            name=agent_data.get("name", ""),
            description=agent_data.get("intro", ""),
            personality=agent_data.get("personality", ""),
            scenario=agent_data.get("scenario", ""),
            first_mes=agent_data.get("first_message") or agent_data.get("opening", ""),
            mes_example=agent_data.get("message_example", ""),
            creator_notes=agent_data.get("creator_notes", ""),
            system_prompt=agent_data.get("prompt", ""),
            post_history_instructions=agent_data.get("post_history_instructions", ""),
            alternate_greetings=agent_data.get("alternate_greetings", []),
            character_book=None,  # 需要特殊处理
            tags=agent_data.get("tags", []),
            creator=(
                agent_data.get("creator", {}).get("nickname", "")
                if agent_data.get("creator")
                else ""
            ),
            character_version=agent_data.get("character_version", "1.0"),
            extensions=agent_data.get("extensions", {}),
        )
#角色处理书
        if agent_data.get("character_book"):
            try:
                from app.schemas.character_card import CharacterBook

                card_data.character_book = CharacterBook(**agent_data["character_book"])
            except Exception as e:
                logger.warning(f"解析角色书失败: {e}")

        return CharacterCardV2(data=card_data)

    def _build_system_prompt(self, data: CharacterCardDataV2) -> str:
        """
        构建系统提示词

        Args:
            data: 角色卡数据

        Returns:
            系统提示词
        """
        if data.system_prompt:
            return data.system_prompt
# 从角色卡字段构建提示词
        prompt_parts = []
#角色基本信息
        if data.name:
            prompt_parts.append(f"你是{data.name}。")
# 角色描述
        if data.description:
            prompt_parts.append(f"角色描述：{data.description}")
# 性格特征
        if data.personality:
            prompt_parts.append(f"性格特征：{data.personality}")
#场景设置
        if data.scenario:
            prompt_parts.append(f"场景设定：{data.scenario}")
# 对话示例
        if data.mes_example:
            prompt_parts.append(f"对话风格参考：\n{data.mes_example}")
# 后续历史指令
        if data.post_history_instructions:
            prompt_parts.append(f"重要指示：{data.post_history_instructions}")

        return (
            "\n\n".join(prompt_parts)
            if prompt_parts
            else "你是一个AI助手，请用友好的方式回答用户的问题。"
        )

    def _infer_gender(self, data: CharacterCardDataV2) -> Gender:
        """
        从角色卡数据推断性别

        Args:
            data: 角色卡数据

        Returns:
            推断的性别
        """
# 合并所有文本用于性别推断
        text_to_analyze = " ".join(
            [
                data.name,
                data.description,
                data.personality,
                data.scenario,
                " ".join(data.tags),
            ]
        ).lower()
# 统计关键词出现次数
        gender_scores = {"male": 0, "female": 0, "other": 0}

        for gender, keywords in self.gender_keywords.items():
            for keyword in keywords:
                gender_scores[gender] += len(
                    re.findall(r"\b" + keyword + r"\b", text_to_analyze)
                )
#返回得分最高的性别
        max_gender = max(gender_scores, key=gender_scores.get)

        if gender_scores[max_gender] == 0:
            return Gender.OTHER  # 无法确定时默认为其他

        return {"male": Gender.MALE, "female": Gender.FEMALE, "other": Gender.OTHER}[
            max_gender
        ]

    def _extract_category_from_tags(self, tags: List[str]) -> Optional[str]:
        """
        从标签中提取分类

        Args:
            tags: 标签列表

        Returns:
            分类字符串
        """
        if not tags:
            return None
# 定义分类地图
        category_map = {
            "assistant": "助手",
            "helper": "助手",
            "companion": "伙伴",
            "friend": "朋友",
            "teacher": "老师",
            "student": "学生",
            "professional": "专业人士",
            "celebrity": "名人",
            "character": "角色",
            "anime": "动漫",
            "game": "游戏",
            "fantasy": "幻想",
            "sci-fi": "科幻",
            "romance": "浪漫",
            "adventure": "冒险",
            "mystery": "悬疑",
            "horror": "恐怖",
            "comedy": "喜剧",
            "drama": "戏剧",
        }
# 找到匹配的分类
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in category_map:
                return category_map[tag_lower]
# 如果没有匹配的分类，返回第一个标签
        return tags[0] if tags else None

    def validate_character_card(self, card_data: Dict[str, Any]) -> List[str]:
        """
        验证角色卡数据

        Args:
            card_data: 角色卡数据

        Returns:
            验证错误列表
        """
        errors = []
#检查基本结构
        if not isinstance(card_data, dict):
            errors.append("角色卡数据必须是字典格式")
            return errors
#检查规范版本
        if card_data.get("spec") != "chara_card_v2":
            errors.append("只支持chara_card_v2格式")
#查询数据字段
        data = card_data.get("data", {})
        if not isinstance(data, dict):
            errors.append("角色卡数据缺少data字段")
            return errors
# 检查必需字段
        required_fields = ["name"]
        for field in required_fields:
            if not data.get(field):
                errors.append(f"缺少必需字段: {field}")
#检查字段长度
        if data.get("name") and len(data["name"]) > 30:
            errors.append("角色名称不能超过30个字符")
# 查看索引字段
        array_fields = ["alternate_greetings", "tags"]
        for field in array_fields:
            if field in data and not isinstance(data[field], list):
                errors.append(f"字段{field}必须是数组格式")

        return errors

    def get_supported_features(self) -> List[str]:
        """
        获取支持的功能列表

        Returns:
            支持的功能列表
        """
        return [
            "basic_info",
            "personality",
            "scenario",
            "first_message",
            "message_example",
            "system_prompt",
            "creator_notes",
            "post_history_instructions",
            "alternate_greetings",
            "character_book",
            "tags",
            "extensions",
        ]
