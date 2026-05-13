#!/usr/bin/env python3
"""
标签解析器测试
"""

import unittest

from tools.scripts.agent_tags_migration.tag_parser import TagParser
from tools.scripts.agent_tags_migration.tests.sample_data import (
    EXPECTED_RESULTS,
    SAMPLE_PERSONALITIES,
)


class TestTagParser(unittest.TestCase):
    """标签解析器测试类"""

    def setUp(self):
        """设置测试环境"""
        self.parser = TagParser()

    def test_extract_tags_basic(self):
        """测试基本的标签提取功能"""
        # 测试标准格式
        result = self.parser.extract_tags_from_personality(
            SAMPLE_PERSONALITIES[0], "test-agent-1", "Test Agent"
        )

        self.assertTrue(result.extraction_success)
        self.assertEqual(result.extracted_tags, ["Dancer", "Sexy", "Exotic", "Singer"])
        self.assertIsNotNone(result.character_info)
        self.assertEqual(result.character_info.name, "Layla")

    def test_extract_tags_double_quotes(self):
        """测试双引号JSON格式"""
        result = self.parser.extract_tags_from_personality(
            SAMPLE_PERSONALITIES[2], "test-agent-2", "Test Agent 2"
        )

        self.assertTrue(result.extraction_success)
        self.assertEqual(
            result.extracted_tags, ["Creative", "Artistic", "Passionate", "Talented"]
        )

    def test_extract_tags_mixed_quotes(self):
        """测试混合引号格式"""
        result = self.parser.extract_tags_from_personality(
            SAMPLE_PERSONALITIES[3], "test-agent-3", "Test Agent 3"
        )

        self.assertTrue(result.extraction_success)
        self.assertEqual(
            result.extracted_tags, ["Teacher", "Kind", "Patient", "Caring"]
        )

    def test_extract_tags_no_character_info(self):
        """测试没有Character info的情况"""
        result = self.parser.extract_tags_from_personality(
            SAMPLE_PERSONALITIES[11], "test-agent-4", "Test Agent 4"
        )

        self.assertFalse(result.extraction_success)
        self.assertEqual(result.extracted_tags, [])
        self.assertIn("未找到Character info结构", result.error_message)

    def test_extract_tags_empty_tags(self):
        """测试空tags字段"""
        result = self.parser.extract_tags_from_personality(
            SAMPLE_PERSONALITIES[7], "test-agent-5", "Test Agent 5"
        )

        self.assertFalse(result.extraction_success)
        self.assertEqual(result.extracted_tags, [])

    def test_extract_tags_malformed_json(self):
        """测试格式错误的JSON"""
        result = self.parser.extract_tags_from_personality(
            SAMPLE_PERSONALITIES[10], "test-agent-6", "Test Agent 6"
        )

        self.assertFalse(result.extraction_success)
        self.assertEqual(result.extracted_tags, [])

    def test_extract_tags_python_literal_with_json_null(self):
        """测试Python字面量中兼容JSON null常量"""
        personality = """
        ##Character info:
        {'name': 'Mike', 'age': null, 'gender': 'MALE', 'tags': 'Calm, Reliable'}
        """

        result = self.parser.extract_tags_from_personality(
            personality, "test-agent-json-null", "Test Agent JSON Null"
        )

        self.assertTrue(result.extraction_success)
        self.assertEqual(result.extracted_tags, ["Calm", "Reliable"])
        self.assertIsNotNone(result.character_info)
        self.assertIsNone(result.character_info.age)

    def test_extract_tags_rejects_non_literal_expression(self):
        """测试拒绝非字面量表达式，避免执行任意代码"""
        personality = """
        ##Character info:
        {'name': 'Evil', 'tags': __import__('os').system('echo pwned')}
        """

        result = self.parser.extract_tags_from_personality(
            personality, "test-agent-expression", "Test Agent Expression"
        )

        self.assertFalse(result.extraction_success)
        self.assertEqual(result.extracted_tags, [])

    def test_extract_tags_null_personality(self):
        """测试空personality"""
        result = self.parser.extract_tags_from_personality(
            None, "test-agent-7", "Test Agent 7"
        )

        self.assertFalse(result.extraction_success)
        self.assertIn("personality字段为空", result.error_message)

    def test_parse_tags_string(self):
        """测试标签字符串解析"""
        # 测试基本分割
        tags = self.parser._parse_tags_string("Dancer, Sexy, Exotic, Singer")
        self.assertEqual(tags, ["Dancer", "Sexy", "Exotic", "Singer"])

        # 测试去除空格
        tags = self.parser._parse_tags_string(" Artist , Creative , Passionate ")
        self.assertEqual(tags, ["Artist", "Creative", "Passionate"])

        # 测试去重
        tags = self.parser._parse_tags_string("Tag1, tag1, TAG1, Tag2")
        self.assertEqual(tags, ["Tag1", "Tag2"])

        # 测试空字符串
        tags = self.parser._parse_tags_string("")
        self.assertEqual(tags, [])

        # 测试包含引号的标签
        tags = self.parser._parse_tags_string("'Artist', \"Creative\", Passionate")
        self.assertEqual(tags, ["Artist", "Creative", "Passionate"])

    def test_clean_tag(self):
        """测试单个标签清理"""
        # 测试正常标签
        self.assertEqual(self.parser._clean_tag("artist"), "Artist")
        self.assertEqual(self.parser._clean_tag("CREATIVE"), "Creative")

        # 测试去除引号
        self.assertEqual(self.parser._clean_tag("'dancer'"), "Dancer")
        self.assertEqual(self.parser._clean_tag('"singer"'), "Singer")

        # 测试去除空格
        self.assertEqual(self.parser._clean_tag("  performer  "), "Performer")

        # 测试长度限制
        self.assertIsNone(self.parser._clean_tag("a"))  # 太短
        self.assertIsNone(self.parser._clean_tag("a" * 51))  # 太长

        # 测试空标签
        self.assertIsNone(self.parser._clean_tag(""))
        self.assertIsNone(self.parser._clean_tag(None))

    def test_normalize_tags(self):
        """测试标签标准化"""
        tags = ["hot", "beautiful", "smart", "unique"]
        normalized = self.parser.normalize_tags(tags)

        # 检查映射
        self.assertIn("Sexy", normalized)  # hot -> Sexy
        self.assertIn("Beautiful", normalized)  # beautiful -> Beautiful
        self.assertIn("Intelligent", normalized)  # smart -> Intelligent
        self.assertIn("Unique", normalized)  # unique -> Unique (首字母大写)

    def test_validate_tags(self):
        """测试标签验证"""
        tags = [
            "ValidTag",
            "a",
            "123",
            "Normal-Tag",
            "Tag With Spaces",
            "Too@Many!Special#Chars",
        ]
        valid, invalid = self.parser.validate_tags(tags)

        self.assertIn("ValidTag", valid)
        self.assertIn("Normal-Tag", valid)
        self.assertIn("Tag With Spaces", valid)

        self.assertIn("a", invalid)  # 太短
        self.assertIn("123", invalid)  # 全数字
        self.assertIn("Too@Many!Special#Chars", invalid)  # 特殊字符

    def test_comprehensive_extraction(self):
        """综合测试：测试所有样本数据"""
        for i, (personality, expected) in enumerate(
            zip(SAMPLE_PERSONALITIES, EXPECTED_RESULTS)
        ):
            with self.subTest(i=i):
                result = self.parser.extract_tags_from_personality(
                    personality, f"test-agent-{i}", f"Test Agent {i}"
                )

                if expected:  # 如果预期有结果
                    self.assertTrue(result.extraction_success, f"样本 {i} 应该提取成功")
                    # 比较标签（忽略大小写和顺序）
                    result_tags_lower = [tag.lower() for tag in result.extracted_tags]
                    expected_tags_lower = [tag.lower() for tag in expected]
                    self.assertEqual(
                        set(result_tags_lower),
                        set(expected_tags_lower),
                        f"样本 {i} 的标签不匹配",
                    )
                else:  # 如果预期没有结果
                    self.assertFalse(
                        result.extraction_success or result.extracted_tags,
                        f"样本 {i} 不应该提取成功",
                    )


if __name__ == "__main__":
    unittest.main()
