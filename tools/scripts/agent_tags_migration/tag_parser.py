#!/usr/bin/env python3
"""
标签解析器
从personality字段中提取和解析标签信息
"""

import ast
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .models import CharacterInfo, TagExtractionResult


class TagParser:
    """标签解析器类"""

    def __init__(self):
        # 匹配Character info的正则表达式
        self.character_info_patterns = [
            r"##\s*Charactor\s+info:\s*(\{.*?\})",  # 原始格式（拼写错误）
            r"##\s*Character\s+info:\s*(\{.*?\})",  # 正确拼写
            r"##\s*角色信息:\s*(\{.*?\})",  # 中文
            r"Character\s+Info:\s*(\{.*?\})",  # 大小写变体
            r"character\s+info:\s*(\{.*?\})",  # 小写
        ]

        # 匹配tags的正则表达式
        self.tag_patterns = [
            r"'tags':\s*'([^']+)'",  # 'tags': 'value'
            r'"tags":\s*"([^"]+)"',  # "tags": "value"
            r"'tags':\s*\"([^\"]+)\"",  # 'tags': "value"
            r'"tags":\s*\'([^\']+)\'',  # "tags": 'value'
        ]

    def extract_tags_from_personality(
        self, personality: str, agent_id: str, agent_name: str
    ) -> TagExtractionResult:
        """
        从personality字段中提取标签

        Args:
            personality: 角色性格描述文本
            agent_id: 智能体ID
            agent_name: 智能体名称

        Returns:
            TagExtractionResult: 提取结果
        """
        result = TagExtractionResult(agent_id=agent_id, agent_name=agent_name)

        if not personality or not isinstance(personality, str):
            result.error_message = "personality字段为空或不是字符串"
            return result

        try:
            # 尝试提取Character info
            character_info, extraction_method = self._extract_character_info(
                personality
            )

            if character_info:
                result.character_info = character_info
                result.extraction_method = extraction_method

                # 从Character info中提取tags
                if character_info.tags:
                    tags = self._parse_tags_string(character_info.tags)
                    if tags:
                        result.extracted_tags = tags
                        result.extraction_success = True
                    else:
                        result.error_message = (
                            f"无法解析tags字符串: {character_info.tags}"
                        )
                else:
                    result.error_message = "Character info中没有tags字段"
            else:
                result.error_message = "未找到Character info结构"

        except Exception as e:
            result.error_message = f"解析过程出错: {str(e)}"

        return result

    def _extract_character_info(
        self, text: str
    ) -> Tuple[Optional[CharacterInfo], Optional[str]]:
        """
        提取Character info结构

        Returns:
            Tuple[CharacterInfo, str]: (角色信息对象, 提取方法)
        """
        # 尝试各种正则表达式模式
        for i, pattern in enumerate(self.character_info_patterns):
            matches = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                json_str = matches.group(1)
                character_info = self._parse_character_info_json(json_str)
                if character_info:
                    return character_info, f"regex_pattern_{i+1}"

        return None, None

    def _parse_character_info_json(
        self, json_str: str
    ) -> Optional[CharacterInfo]:
        """
        解析Character info的JSON字符串

        Args:
            json_str: JSON字符串

        Returns:
            CharacterInfo对象或None
        """
        # 清理JSON字符串
        json_str = json_str.strip()

        # 尝试多种解析方法
        parsing_methods = [
            self._parse_with_json,
            self._parse_with_ast,
            self._parse_with_safe_literal_ast,
            self._parse_with_regex,
        ]

        for method in parsing_methods:
            try:
                result = method(json_str)
                if result:
                    return result
            except Exception:
                continue

        return None

    def _parse_with_json(self, json_str: str) -> Optional[CharacterInfo]:
        """使用标准JSON解析"""
        try:
            data = json.loads(json_str)
            return CharacterInfo(**data)
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    def _parse_with_ast(self, json_str: str) -> Optional[CharacterInfo]:
        """使用ast.literal_eval解析"""
        try:
            data = ast.literal_eval(json_str)
            if isinstance(data, dict):
                return CharacterInfo(**data)
        except (ValueError, SyntaxError, TypeError):
            return None
        return None

    def _parse_with_safe_literal_ast(
        self, json_str: str
    ) -> Optional[CharacterInfo]:
        """使用安全AST解析兼容JSON常量的Python字面量"""
        try:
            parsed = ast.parse(json_str, mode="eval")
            data = self._convert_literal_node(parsed.body)
            if isinstance(data, dict):
                return CharacterInfo(**data)
        except (SyntaxError, TypeError, ValueError):
            return None
        return None

    def _convert_literal_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            constants = {"null": None, "true": True, "false": False}
            if node.id in constants:
                return constants[node.id]
            raise ValueError(f"unsupported name in literal: {node.id}")

        if isinstance(node, ast.Dict):
            return {
                self._convert_literal_node(key): self._convert_literal_node(
                    value
                )
                for key, value in zip(node.keys, node.values)
            }

        if isinstance(node, (ast.List, ast.Tuple)):
            return [self._convert_literal_node(item) for item in node.elts]

        if isinstance(node, ast.UnaryOp) and isinstance(
            node.op, (ast.UAdd, ast.USub)
        ):
            value = self._convert_literal_node(node.operand)
            if isinstance(value, (int, float)):
                return value if isinstance(node.op, ast.UAdd) else -value

        raise ValueError(f"unsupported literal node: {type(node).__name__}")

    def _parse_with_regex(self, json_str: str) -> Optional[CharacterInfo]:
        """使用正则表达式直接提取tags"""
        try:
            for pattern in self.tag_patterns:
                match = re.search(pattern, json_str)
                if match:
                    tags_str = match.group(1)
                    return CharacterInfo(tags=tags_str)
        except Exception:
            return None
        return None

    def _parse_tags_string(self, tags_str: str) -> List[str]:
        """
        解析tags字符串为列表

        Args:
            tags_str: 标签字符串，如 "Dancer, Sexy, Exotic, Singer"

        Returns:
            标签列表
        """
        if not tags_str:
            return []

        # 按常见分隔符分割
        tags = [tag.strip() for tag in re.split(r"[,;]", tags_str)]

        # 过滤和清理
        cleaned_tags = []
        for tag in tags:
            cleaned_tag = self._clean_tag(tag)
            if cleaned_tag:
                cleaned_tags.append(cleaned_tag)

        # 去重并保持顺序
        unique_tags = []
        seen = set()
        for tag in cleaned_tags:
            tag_lower = tag.lower()
            if tag_lower not in seen:
                unique_tags.append(tag)
                seen.add(tag_lower)

        return unique_tags

    def _clean_tag(self, tag: str) -> Optional[str]:
        """
        清理单个标签

        Args:
            tag: 原始标签

        Returns:
            清理后的标签或None
        """
        if not tag:
            return None

        # 去除空格和引号
        tag = tag.strip().strip("'\"")

        # 长度检查
        if len(tag) < 2 or len(tag) > 50:
            return None

        # 首字母大写
        tag = tag.capitalize()

        return tag

    def normalize_tags(self, tags: List[str]) -> List[str]:
        """
        标准化标签列表

        Args:
            tags: 标签列表

        Returns:
            标准化后的标签列表
        """
        normalized = []

        # 标签映射（统一相似标签）
        tag_mappings = {
            "hot": "Sexy",
            "beautiful": "Beautiful",
            "cute": "Cute",
            "smart": "Intelligent",
            "clever": "Intelligent",
            "funny": "Humorous",
            "witty": "Humorous",
        }

        for tag in tags:
            # 转换为小写进行映射查找
            tag_lower = tag.lower()
            if tag_lower in tag_mappings:
                normalized_tag = tag_mappings[tag_lower]
            else:
                normalized_tag = tag.capitalize()

            # 避免重复
            if normalized_tag not in normalized:
                normalized.append(normalized_tag)

        return normalized

    def validate_tags(self, tags: List[str]) -> Tuple[List[str], List[str]]:
        """
        验证标签列表

        Args:
            tags: 标签列表

        Returns:
            Tuple[valid_tags, invalid_tags]: (有效标签, 无效标签)
        """
        valid_tags = []
        invalid_tags = []

        for tag in tags:
            if self._is_valid_tag(tag):
                valid_tags.append(tag)
            else:
                invalid_tags.append(tag)

        return valid_tags, invalid_tags

    def _is_valid_tag(self, tag: str) -> bool:
        """
        检查标签是否有效

        Args:
            tag: 标签

        Returns:
            是否有效
        """
        if not tag or not isinstance(tag, str):
            return False

        # 长度检查
        if len(tag) < 2 or len(tag) > 50:
            return False

        # 字符检查（允许字母、数字、空格、连字符）
        if not re.match(r"^[a-zA-Z0-9\s\-]+$", tag):
            return False

        # 不能全是数字
        if tag.isdigit():
            return False

        return True

    def get_stats_from_results(
        self, results: List[TagExtractionResult]
    ) -> Dict[str, Any]:
        """
        从提取结果中生成统计信息

        Args:
            results: 提取结果列表

        Returns:
            统计信息字典
        """
        stats = {
            "total_processed": len(results),
            "successful_extractions": sum(
                1 for r in results if r.extraction_success
            ),
            "failed_extractions": sum(
                1 for r in results if not r.extraction_success
            ),
            "total_unique_tags": 0,
            "most_common_tags": {},
            "extraction_methods": {},
            "error_types": {},
        }

        # 统计标签
        all_tags = []
        for result in results:
            if result.extraction_success:
                all_tags.extend(result.extracted_tags)

                # 统计提取方法
                method = result.extraction_method or "unknown"
                stats["extraction_methods"][method] = (
                    stats["extraction_methods"].get(method, 0) + 1
                )
            else:
                # 统计错误类型
                error = result.error_message or "unknown_error"
                stats["error_types"][error] = (
                    stats["error_types"].get(error, 0) + 1
                )

        # 标签频率统计
        from collections import Counter

        tag_counter = Counter(all_tags)
        stats["most_common_tags"] = dict(tag_counter.most_common(20))
        stats["total_unique_tags"] = len(tag_counter)

        return stats
