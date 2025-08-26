"""问题文件解析服务"""

import csv
import io
import json
import logging
from typing import Any, Dict, List

from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)


class QuestionParserService:
    """问题解析服务 - 支持多种格式的问题文件解析"""

    @staticmethod
    async def parse_questions_file(file: UploadFile) -> List[str]:
        """解析问题文件，支持json格式"""

        content = await file.read()
        filename = file.filename or ""

        if not filename.endswith(".json"):
            raise ValueError(f"不支持的文件类型: {filename}")
        return QuestionParserService._parse_json(content)

    @staticmethod
    def _parse_txt(content: bytes) -> List[str]:
        """解析TXT文件"""
        try:
            # 尝试不同的编码
            text = None
            for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
                try:
                    text = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if text is None:
                raise ValueError("无法识别文件编码")

            # 按行分割，过滤空行
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            if not lines:
                raise ValueError("文件为空或无有效问题")

            # 简单的问题验证
            questions = []
            for i, line in enumerate(lines, 1):
                # 移除行号（如果存在）
                line = QuestionParserService._remove_line_number(line)

                if len(line) < 5:
                    logger.warning(f"第{i}行问题过短，已跳过: {line}")
                    continue

                questions.append(line)

            if not questions:
                raise ValueError("没有找到有效的问题")

            return questions

        except Exception as e:
            raise ValueError(f"TXT文件解析失败: {str(e)}")

    @staticmethod
    def _parse_csv(content: bytes) -> List[str]:
        """解析CSV文件"""
        try:
            # 解码内容
            text = None
            for encoding in ["utf-8", "gbk", "gb2312"]:
                try:
                    text = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if text is None:
                raise ValueError("无法识别文件编码")

            # 使用CSV reader
            csv_file = io.StringIO(text)
            reader = csv.reader(csv_file)

            questions = []
            for row_num, row in enumerate(reader, 1):
                if not row:  # 空行
                    continue

                # 取第一列作为问题，如果有多列则合并
                if len(row) == 1:
                    question = row[0].strip()
                else:
                    # 可能是多列格式，尝试找到问题列
                    question = QuestionParserService._extract_question_from_row(row)

                if question and len(question) >= 5:
                    questions.append(question)
                else:
                    logger.warning(f"第{row_num}行无效问题，已跳过: {row}")

            if not questions:
                raise ValueError("CSV文件中没有找到有效的问题")

            return questions

        except Exception as e:
            raise ValueError(f"CSV文件解析失败: {str(e)}")

    @staticmethod
    def _parse_json(content: bytes) -> List[str]:
        """解析JSON文件"""
        try:
            # 解码JSON
            text = content.decode("utf-8")
            data = json.loads(text)

            questions = []

            # 处理不同的JSON结构
            if isinstance(data, list):
                # 数组格式: ["question1", "question2", ...]
                for item in data:
                    if isinstance(item, str):
                        question = item.strip()
                        if question:  # 只要不是空字符串就保留
                            questions.append(question)
                    elif isinstance(item, dict):
                        # 对象数组格式: [{"question": "...", "other": "..."}, ...]
                        question = QuestionParserService._extract_question_from_dict(
                            item
                        )
                        if question:
                            questions.append(question)

            elif isinstance(data, dict):
                # 对象格式
                if "questions" in data and isinstance(data["questions"], list):
                    # {"questions": ["q1", "q2", ...]}
                    for item in data["questions"]:
                        if isinstance(item, str):
                            question = item.strip()
                            if question:  # 只要不是空字符串就保留
                                questions.append(question)
                        elif isinstance(item, dict):
                            question = (
                                QuestionParserService._extract_question_from_dict(item)
                            )
                            if question:
                                questions.append(question)
                else:
                    # 可能是单个问题对象
                    question = QuestionParserService._extract_question_from_dict(data)
                    if question:
                        questions.append(question)

            if not questions:
                raise ValueError("JSON文件中没有找到有效的问题")

            return questions

        except json.JSONDecodeError as e:
            raise ValueError(f"JSON格式错误: {str(e)}")
        except Exception as e:
            raise ValueError(f"JSON文件解析失败: {str(e)}")

    @staticmethod
    def _auto_parse(content: bytes) -> List[str]:
        """自动检测并解析文件格式"""

        # 尝试JSON格式
        try:
            return QuestionParserService._parse_json(content)
        except:
            pass

        # 尝试CSV格式
        try:
            return QuestionParserService._parse_csv(content)
        except:
            pass

        # 最后尝试TXT格式
        try:
            return QuestionParserService._parse_txt(content)
        except Exception as e:
            raise ValueError(f"无法识别文件格式，解析失败: {str(e)}")

    @staticmethod
    def _remove_line_number(line: str) -> str:
        """移除行号前缀，如 '1. 问题内容' -> '问题内容'"""
        import re

        # 匹配行号模式: 数字 + 点/括号/空格
        pattern = r"^\s*\d+[\.\)]\s*"
        return re.sub(pattern, "", line).strip()

    @staticmethod
    def _extract_question_from_row(row: List[str]) -> str:
        """从CSV行中提取问题"""
        # 寻找最可能是问题的列（通常是最长的列）
        candidates = [col.strip() for col in row if col.strip()]
        if not candidates:
            return ""

        # 返回最长的列作为问题
        return max(candidates, key=len)

    @staticmethod
    def _extract_question_from_dict(obj: Dict[str, Any]) -> str:
        """从字典对象中提取问题"""
        # 常见的问题字段名
        question_fields = [
            "question",
            "q",
            "query",
            "text",
            "content",
            "prompt",
            "input",
            "message",
            "问题",
            "内容",
        ]

        for field in question_fields:
            if field in obj and isinstance(obj[field], str):
                question = obj[field].strip()
                if question:  # 只要不是空字符串就保留
                    return question

        # 如果没有找到明确的问题字段，尝试取第一个字符串值
        for value in obj.values():
            if isinstance(value, str):
                question = value.strip()
                if question:  # 只要不是空字符串就保留
                    return question

        return ""

    @staticmethod
    def validate_questions(questions: List[str]) -> Dict[str, Any]:
        """验证问题列表的质量"""

        if not questions:
            return {
                "is_valid": False,
                "issues": ["问题列表为空"],
                "stats": {"total": 0, "valid": 0, "duplicates": 0},
            }

        issues = []
        warnings = []

        # 检查重复问题
        unique_questions = set()
        duplicates = []
        for i, q in enumerate(questions):
            if q.lower() in unique_questions:
                duplicates.append(f"第{i+1}个问题重复: {q[:50]}...")
            else:
                unique_questions.add(q.lower())

        if duplicates:
            issues.extend(duplicates[:5])  # 只显示前5个重复
            if len(duplicates) > 5:
                issues.append(f"...还有{len(duplicates)-5}个重复问题")

        # 检查问题质量
        short_questions = [i + 1 for i, q in enumerate(questions) if len(q) < 10]
        long_questions = [i + 1 for i, q in enumerate(questions) if len(q) > 500]

        # 检查编码问题
        encoding_issues = []
        for i, q in enumerate(questions):
            if "?" in q.replace("？", "").replace("?", ""):  # 排除正常的问号
                if q.count("?") > 2:  # 多个问号可能是编码问题
                    encoding_issues.append(i + 1)

        if encoding_issues:
            warnings.append(f"第{encoding_issues[:3]}行可能存在编码问题")

        stats = {
            "total": len(questions),
            "valid": len(questions) - len(duplicates),
            "duplicates": len(duplicates),
            "short_questions": len(short_questions),
            "long_questions": len(long_questions),
        }

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "stats": stats,
        }
