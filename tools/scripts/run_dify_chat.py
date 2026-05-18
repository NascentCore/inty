#!/usr/bin/env python3
# CREATED_BY_AGENT
"""
调用 OpenRouter 生成角色，再通过 Dify API 创建角色的定时脚本

默认使用 OpenRouter 模型 mistralai/devstral-2512。

从环境变量读取：
- OpenRouter：OPENROUTER_API_KEY 或 OPENAI_API_KEY
- DIFY_API_KEY: Dify API 密钥

数据库配置文件默认使用 tools/scripts/sync_agents_dev_to_prod/config.yaml.example
"""

import asyncio
import json
import logging
import os
import random
import sys
from pathlib import Path
from typing import Any

import cyclopts
import requests
import yaml
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.agent import Agent

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MAX_EXCLUDED_NAMES_IN_PROMPT = 100

app = cyclopts.App()

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
from loguru import logger


class GeneratedCharacter(BaseModel):
    """单个角色的结构化输出。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, description="Character full name")
    description: str = Field(
        min_length=1,
        description="One-sentence scenario that motivates user to choose her",
    )


class GeneratedCharactersResponse(BaseModel):
    """角色生成的结构化输出。"""

    model_config = ConfigDict(extra="forbid")

    characters: list[GeneratedCharacter] = Field(
        min_length=10,
        max_length=10,
        description="Exactly 10 generated characters",
    )


OPENAI_CHARACTER_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "generated_characters_response",
        "strict": True,
        "schema": GeneratedCharactersResponse.model_json_schema(),
    },
}


def parse_generated_characters(raw_json: str) -> list[dict[str, str]]:
    """使用 Pydantic 模型校验并解析角色生成结果。"""

    try:
        parsed = GeneratedCharactersResponse.model_validate_json(raw_json)
    except ValidationError as e:
        logger.error(f"角色结构化输出校验失败: {e}")
        logger.debug(f"模型原始输出片段: {raw_json[:2000]}")
        raise

    return [item.model_dump() for item in parsed.characters]


def load_config(config_path: str) -> dict:
    """加载配置文件

    Args:
        config_path: 配置文件路径，相对于脚本所在目录

    Returns:
        配置字典
    """
    config_file = Path(__file__).parent / config_path
    if not config_file.exists():
        logger.error(f"配置文件不存在: {config_file}")
        sys.exit(1)

    logger.info(f"使用配置文件: {config_file}")
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_db_url(db_config: dict) -> str:
    """创建数据库连接URL"""
    return (
        f"postgresql+asyncpg://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['db']}"
    )


async def fetch_existing_agent_names(session: AsyncSession) -> list[str]:
    """查询数据库中已有的角色名称

    Args:
        session: 数据库会话

    Returns:
        角色名称列表
    """
    result = await session.execute(
        select(Agent.name).where(Agent.deleted_at.is_(None))
    )
    names = [row[0] for row in result.all()]
    logger.info(f"数据库中已有 {len(names)} 个角色")
    return names


def _normalize_name(name: str) -> str:
    """标准化名称用于去重比对（忽略大小写与首尾空格）"""
    return " ".join(name.strip().lower().split())


def prepare_characters_for_dify(
    generated_characters: list[dict[str, Any]],
    existing_names: list[str],
) -> list[dict[str, str]]:
    """
    过滤无效/重复角色，并打散顺序避免每天命中同一批名字。

    - 去除 name/description 缺失项
    - 去除与数据库现有角色重名（大小写不敏感）
    - 去除当前批次内重名
    """
    existing_name_set = {
        _normalize_name(name)
        for name in existing_names
        if isinstance(name, str) and name.strip()
    }
    seen_name_set: set[str] = set()
    prepared: list[dict[str, str]] = []

    for idx, character in enumerate(generated_characters):
        if not isinstance(character, dict):
            logger.warning(f"跳过第 {idx + 1} 个角色：数据格式非法")
            continue

        name = str(character.get("name", "")).strip()
        description = str(character.get("description", "")).strip()
        if not name or not description:
            logger.warning(f"跳过第 {idx + 1} 个角色：name 或 description 为空")
            continue

        normalized_name = _normalize_name(name)
        if normalized_name in existing_name_set:
            logger.info(f"跳过重名角色（数据库已存在）：{name}")
            continue
        if normalized_name in seen_name_set:
            logger.info(f"跳过重名角色（本批次重复）：{name}")
            continue

        seen_name_set.add(normalized_name)
        prepared.append({"name": name, "description": description})

    random.SystemRandom().shuffle(prepared)
    logger.info(
        f"候选角色过滤完成：原始 {len(generated_characters)}，可用 {len(prepared)}"
    )
    return prepared


def build_dify_payload(character: dict[str, str]) -> dict[str, Any]:
    """构建 Dify 请求体，结构化传递 name/description，避免仅依赖 query 文本解析。"""
    query = f"{character['description']}, name is {character['name']}"
    return {
        "inputs": {
            "visibility": "PRIVATE",
            "source": "AUTO_GENERATED",
            # 兼容不同 Dify 工作流变量命名
            "name": character["name"],
            "character_name": character["name"],
            "description": character["description"],
            "character_description": character["description"],
        },
        "query": query,
        "response_mode": "blocking",
        "user": "github-action",
    }


def generate_characters(
    existing_names: list[str],
    model: str = "mistralai/devstral-2512",
    *,
    openrouter_api_key: str | None = None,
) -> list[dict]:
    """调用 OpenRouter 生成 10 个角色信息

    Args:
        existing_names: 数据库中已有的角色名称列表
        model: OpenRouter 模型名，默认 mistralai/devstral-2512
        openrouter_api_key: OpenRouter API 密钥，OpenRouter 时必填

    Returns:
        角色列表，每个角色包含 name 和 description
    """
    excluded_name_limit = MAX_EXCLUDED_NAMES_IN_PROMPT
    excluded_names_text = (
        ", ".join(existing_names[:excluded_name_limit])
        if existing_names
        else "none"
    )
    if len(existing_names) > excluded_name_limit:
        excluded_names_text += (
            f" (and {len(existing_names) - excluded_name_limit} more)"
        )

    prompt = f"""Generate 10 diverse character profiles for an AI companion app. All character must be female and 
Each character should have:
- name: A unique first name and a unique last name, name should match the cultural background of the character, like a Franch person should have a Franch name etc.
- description: A sentence description that includes:
  1. How the user encounters her (a specific, direct, romantic or conflict-ridden scenario based on real American life)
  2. This description should immediately motivate users to choose this character.

Make the characters diverse in name and scenario.

IMPORTANT: Do NOT use any of these existing names: {excluded_names_text}"""

    if "/" not in model:
        raise ValueError(
            "仅支持 OpenRouter 模型名（需包含 '/'），例如 google/gemini-2.5-pro"
        )
    if not openrouter_api_key:
        raise ValueError(
            "使用 OpenRouter 模型时需设置 OPENROUTER_API_KEY 或 OPENAI_API_KEY"
        )
    logger.info(f"调用 OpenRouter 生成角色，model={model}")
    client = OpenAI(api_key=openrouter_api_key, base_url=OPENROUTER_BASE_URL)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=OPENAI_CHARACTER_RESPONSE_FORMAT,
            stream=False,
        )
        message = response.choices[0].message
        refusal = getattr(message, "refusal", None)
        if refusal:
            raise ValueError(f"OpenRouter 模型拒绝输出结构化结果: {refusal}")

        text = (message.content or "").strip()
        if not text:
            raise ValueError("OpenRouter 返回空响应")
    except Exception as e:
        logger.error(f"OpenRouter 调用失败: {e}")
        raise

    characters = parse_generated_characters(text)
    logger.info(f"成功生成 {len(characters)} 个角色")
    logger.debug(
        f"角色列表: {json.dumps(characters, indent=2, ensure_ascii=False)}"
    )
    return characters


def call_dify(dify_api_key: str, character: dict) -> bool:
    """调用 Dify API 为单个角色创建

    Args:
        dify_api_key: Dify API 密钥
        character: 角色信息，包含 name 和 description

    Returns:
        是否成功
    """
    api_base = "https://api.dify.ai"
    endpoint = f"{api_base}/v1/chat-messages"

    headers = {
        "Authorization": f"Bearer {dify_api_key}",
        "Content-Type": "application/json",
    }

    payload = build_dify_payload(character)
    query = payload["query"]

    logger.info(f"为角色 '{character['name']}' 调用 Dify API...")
    logger.debug(f"query: {query}")

    try:
        response = requests.post(
            endpoint, headers=headers, json=payload, timeout=180
        )
        logger.debug(f"响应状态码: {response.status_code}")
        logger.debug(f"响应内容: {response.text[:500]}")

        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"角色 '{character['name']}' 创建成功")
            return True
        else:
            logger.warning(
                f"角色 '{character['name']}' 创建失败: {response.status_code} - {response.text}"
            )
            return False

    except requests.RequestException as e:
        logger.warning(f"角色 '{character['name']}' 请求失败: {e}")
        return False


@app.default
async def main(
    config: str = "sync_agents_dev_to_prod/config.yaml.example",
    target_count: int = 3,
    model: str = "mistralai/devstral-2512",
) -> int:
    """主函数：查询数据库、生成角色并批量创建

    Args:
        config: 配置文件路径，相对于 tools/scripts/ 目录（默认: sync_agents_dev_to_prod/config.yaml.example）
        target_count: 目标创建角色数量（默认: 3，最大: 10）
        model: OpenRouter 模型名（默认: mistralai/devstral-2512）
    """
    if target_count < 1 or target_count > 10:
        logger.error("target_count 必须在 1-10 之间")
        return 1
    if "/" not in model:
        logger.error(
            "仅支持 OpenRouter 模型名（需包含 '/'），例如 google/gemini-2.5-pro"
        )
        return 1

    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get(
        "OPENAI_API_KEY"
    )
    dify_api_key = os.environ.get("DIFY_API_KEY")

    if not openrouter_api_key:
        logger.error(
            "使用 OpenRouter 模型时需设置环境变量 OPENROUTER_API_KEY 或 OPENAI_API_KEY"
        )
        return 1
    if not dify_api_key:
        logger.error("环境变量 DIFY_API_KEY 未设置")
        return 1

    # 加载数据库配置
    config_data = load_config(config)
    db_config = config_data.get("dev_database") or config_data.get("database")
    if not db_config:
        logger.error("配置文件中未找到 prod_database 或 database 配置")
        return 1

    db_url = create_db_url(db_config)
    engine = create_async_engine(db_url, echo=False)
    Session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        async with Session() as session:
            # 查询已有角色名称
            existing_names = await fetch_existing_agent_names(session)

            # 生成 10 个角色
            characters = generate_characters(
                existing_names,
                model,
                openrouter_api_key=openrouter_api_key,
            )
            characters = prepare_characters_for_dify(characters, existing_names)
            if not characters:
                logger.error("本次没有可用的新角色可提交到 Dify")
                return 1
            if len(characters) < target_count:
                logger.warning(
                    f"可用候选角色仅 {len(characters)} 个，低于目标 {target_count} 个"
                )

            # 循环调用 Dify，达到目标数量即停止
            success_count = 0

            for char in characters:
                if call_dify(dify_api_key, char):
                    success_count += 1
                    logger.info(
                        f"已成功创建 {success_count}/{target_count} 个角色"
                    )
                    if success_count >= target_count:
                        logger.info(
                            f"已达到目标数量 ({target_count})，停止创建"
                        )
                        break

            if success_count < target_count:
                logger.warning(
                    f"仅成功创建 {success_count}/{target_count} 个角色"
                )
                return 1

            logger.info(f"成功完成：共创建 {success_count} 个角色")
            return 0

    except Exception as e:
        logger.error(f"执行失败: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(app())
