# 测试 openrouter_memory 的 llm_qa：FakeOpenAI + 预填 _responses_by_request 断言解析结果

from unittest.mock import patch

import pytest
from pydantic import BaseModel

from app.external_services.fakes.openai import FakeOpenAI
from app.utils.openrouter_memory import (
    DEFAULT_MEMORY_EXTRACTION_MODEL,
    llm_qa,
)


class _TestSummary(BaseModel):
    """最小 Pydantic 模型，用于 llm_qa 测试。"""

    summary: str
    score: int = 0


def test_llm_qa_returns_pydantic_instance_when_fake_returns_valid_json():
    """FakeOpenAI 预填符合 schema 的 JSON 时，llm_qa 返回对应 Pydantic 实例且字段正确。"""
    client = FakeOpenAI()
    system_prompt = "You extract a short summary."
    query = "User said: Hello world."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]
    content = '{"summary": "Greeting exchange", "score": 1}'
    client.register_response(
        messages=messages,
        content=content,
        model=DEFAULT_MEMORY_EXTRACTION_MODEL,
    )
    with patch("app.utils.openrouter_memory.get_base_openai_client", return_value=client):
        result = llm_qa(
            system_prompt=system_prompt,
            query=query,
            output_format=_TestSummary,
            model=DEFAULT_MEMORY_EXTRACTION_MODEL,
        )
    assert isinstance(result, _TestSummary)
    assert result.summary == "Greeting exchange"
    assert result.score == 1


def test_llm_qa_raises_when_content_empty():
    """当模型返回空 content 时，llm_qa 抛出 ValueError。"""
    client = FakeOpenAI()
    system_prompt = "You are helpful."
    query = "Hi"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]
    client.register_response(
        messages=messages,
        content="   ",
        model=DEFAULT_MEMORY_EXTRACTION_MODEL,
    )
    with patch("app.utils.openrouter_memory.get_base_openai_client", return_value=client):
        with pytest.raises(ValueError, match="空 content"):
            llm_qa(
                system_prompt=system_prompt,
                query=query,
                output_format=_TestSummary,
                model=DEFAULT_MEMORY_EXTRACTION_MODEL,
            )
