#!/usr/bin/env python3
# CREATED_BY_AGENT
"""
调用 Gemini 或 OpenRouter 生成角色，再通过 Dify API 创建角色的定时脚本

默认使用 OpenRouter 模型 mistralai/devstral-2512。模型名包含 "/" 时走 OpenRouter，否则走 Gemini。

从环境变量读取：
- OpenRouter：OPENROUTER_API_KEY 或 OPENAI_API_KEY
- Gemini：GOOGLE_API_KEY
- DIFY_API_KEY: Dify API 密钥

数据库配置文件默认使用 scripts/sync_agents_dev_to_prod/config.yaml.example
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import cyclopts
import requests
import yaml
from google import genai
from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.agent import Agent

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

app = cyclopts.App()

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


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
    result = await session.execute(select(Agent.name).where(Agent.deleted_at.is_(None)))
    names = [row[0] for row in result.all()]
    logger.info(f"数据库中已有 {len(names)} 个角色")
    return names


def generate_characters(
    existing_names: list[str],
    model: str = "mistralai/devstral-2512",
    *,
    google_api_key: str | None = None,
    openrouter_api_key: str | None = None,
) -> list[dict]:
    """调用 Gemini 或 OpenRouter 生成 10 个角色信息

    模型名包含 "/" 时使用 OpenRouter（需 openrouter_api_key），否则使用 Gemini（需 google_api_key）。

    Args:
        existing_names: 数据库中已有的角色名称列表
        model: 模型名，默认 mistralai/devstral-2512（OpenRouter）
        google_api_key: Google API 密钥，Gemini 时必填
        openrouter_api_key: OpenRouter API 密钥，OpenRouter 时必填

    Returns:
        角色列表，每个角色包含 name 和 description
    """
    excluded_names_text = ", ".join(existing_names[:100]) if existing_names else "none"
    if len(existing_names) > 100:
        excluded_names_text += f" (and {len(existing_names) - 100} more)"

    prompt = f"""Generate 10 diverse character profiles for a chat companion app. All character must be female and 
Each character should have:
- name: A unique first name
- description: A sentence description that includes:
  1. How the user encounters her (a specific, direct, romantic or conflict-ridden scenario based on real American life)
  2. This description should immediately motivate users to choose this character.

Return ONLY a valid JSON array in this exact format:
[
  {{"name": "Alice", "description": "Your sister's female classmate has had a crush on you since childhood. She's sitting on your bed crying right now."}},
  {{"name": "Marcus", "description": "Your stepsister is moving in with you soon."}}
]

Make the characters diverse in name and scenario.

IMPORTANT: Do NOT use any of these existing names: {excluded_names_text}"""

    use_openrouter = "/" in model
    if use_openrouter:
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
                stream=False,
            )
            text = (response.choices[0].message.content or "").strip()
        except Exception as e:
            logger.error(f"OpenRouter 调用失败: {e}")
            raise
    else:
        if not google_api_key:
            raise ValueError("使用 Gemini 模型时需设置 GOOGLE_API_KEY")
        logger.info(f"调用 Gemini 生成角色，model={model}")
        client = genai.Client(api_key=google_api_key)
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            text = response.text.strip()
        except Exception as e:
            logger.error(f"Gemini 调用失败: {e}")
            raise

    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    characters = json.loads(text)
    logger.info(f"成功生成 {len(characters)} 个角色")
    logger.debug(f"角色列表: {json.dumps(characters, indent=2, ensure_ascii=False)}")
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

    query = f"{character['description']}, name is {character['name']}"
    payload = {
        "inputs": {
            "visibility": "PRIVATE",
            "source": "AUTO_GENERATED",
        },
        "query": query,
        "response_mode": "blocking",
        "user": "github-action",
    }

    logger.info(f"为角色 '{character['name']}' 调用 Dify API...")
    logger.debug(f"query: {query}")

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=180)
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
        config: 配置文件路径，相对于 scripts/ 目录（默认: sync_agents_dev_to_prod/config.yaml.example）
        target_count: 目标创建角色数量（默认: 3，最大: 10）
        model: 模型名，含 "/" 为 OpenRouter（默认: mistralai/devstral-2512），否则为 Gemini
    """
    if target_count < 1 or target_count > 10:
        logger.error("target_count 必须在 1-10 之间")
        return 1
    use_openrouter = "/" in model
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get(
        "OPENAI_API_KEY"
    )
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    dify_api_key = os.environ.get("DIFY_API_KEY")

    if use_openrouter and not openrouter_api_key:
        logger.error(
            "使用 OpenRouter 模型时需设置环境变量 OPENROUTER_API_KEY 或 OPENAI_API_KEY"
        )
        return 1
    if not use_openrouter and not google_api_key:
        logger.error("使用 Gemini 模型时需设置环境变量 GOOGLE_API_KEY")
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
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with Session() as session:
            # 查询已有角色名称
            existing_names = await fetch_existing_agent_names(session)

            # 生成 10 个角色
            characters = generate_characters(
                existing_names,
                model,
                google_api_key=google_api_key,
                openrouter_api_key=openrouter_api_key,
            )

            # 循环调用 Dify，达到目标数量即停止
            success_count = 0

            for char in characters:
                if call_dify(dify_api_key, char):
                    success_count += 1
                    logger.info(f"已成功创建 {success_count}/{target_count} 个角色")
                    if success_count >= target_count:
                        logger.info(f"已达到目标数量 ({target_count})，停止创建")
                        break

            if success_count < target_count:
                logger.warning(f"仅成功创建 {success_count}/{target_count} 个角色")
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
