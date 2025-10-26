#!/usr/bin/env python3
"""
Agent prompt字段迁移到角色卡字段的脚本

将现有的prompt内容智能分析并迁移到personality、scenario等角色卡字段中
"""

import asyncio
import re
import logging
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_async_db
from app import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_prompt_content(prompt: str) -> Dict[str, str]:
    """
    智能分析prompt内容，提取角色卡相关信息

    Args:
        prompt: 原始prompt文本

    Returns:
        包含personality、scenario、first_message等字段的字典
    """
    if not prompt:
        return {}

    result = {
        "personality": "",
        "scenario": "",
        "first_message": "",
        "message_example": "",
        "creator_notes": "",
    }

    # 清理文本
    clean_prompt = prompt.strip()

    # 1. 提取角色性格信息
    personality_patterns = [
        r"##\s*personality[:\s]*([^#]+)",
        r"性格[：:]\s*([^。\n]+)",
        r"特点[：:]\s*([^。\n]+)",
        r"你是一个[^，。]+[的性格特征|的人]([^。\n]+)",
        r"扮演.*?([温柔|冷酷|活泼|内向|外向|聪明|善良|调皮|认真|幽默][^。\n]*)",
    ]

    for pattern in personality_patterns:
        match = re.search(pattern, clean_prompt, re.IGNORECASE | re.DOTALL)
        if match:
            personality_text = match.group(1).strip()
            if len(personality_text) > 10:  # 确保提取的内容有意义
                result["personality"] = personality_text[:500]  # 限制长度
                break

    # 2. 提取场景背景信息
    scenario_patterns = [
        r"##\s*scenario[:\s]*([^#]+)",
        r"背景[：:]\s*([^。\n]+)",
        r"设定[：:]\s*([^。\n]+)",
        r"故事背景[：:]\s*([^。\n]+)",
        r"世界观[：:]\s*([^。\n]+)",
        r"在.*?[的世界|的时代|的环境]([^。\n]+)",
    ]

    for pattern in scenario_patterns:
        match = re.search(pattern, clean_prompt, re.IGNORECASE | re.DOTALL)
        if match:
            scenario_text = match.group(1).strip()
            if len(scenario_text) > 10:
                result["scenario"] = scenario_text[:500]
                break

    # 3. 提取对话示例
    example_patterns = [
        r"对话示例[：:]([^#]+)",
        r"例子[：:]([^#]+)",
        r"示例[：:]([^#]+)",
    ]

    for pattern in example_patterns:
        match = re.search(pattern, clean_prompt, re.IGNORECASE | re.DOTALL)
        if match:
            example_text = match.group(1).strip()
            if len(example_text) > 10:
                result["message_example"] = example_text[:1000]
                break

    # 4. 如果没有明确分类，将整个prompt作为personality
    if not result["personality"] and not result["scenario"]:
        # 简化处理：如果prompt较短且有明确的角色描述，放入personality
        if len(clean_prompt) < 300 and (
            "你是" in clean_prompt or "扮演" in clean_prompt
        ):
            result["personality"] = clean_prompt
        else:
            # 较长的prompt分成personality和scenario
            lines = clean_prompt.split("\n")
            if len(lines) > 1:
                result["personality"] = lines[0][:500]
                result["scenario"] = "\n".join(lines[1:])[:500]
            else:
                result["personality"] = clean_prompt[:500]

    # 5. 生成创建者备注
    result["creator_notes"] = f"从原始prompt字段迁移而来，原长度: {len(prompt)}字符"

    return result


async def migrate_single_agent(
    session: AsyncSession, agent: models.Agent, dry_run: bool = True
) -> bool:
    """
    迁移单个Agent的prompt到角色卡字段

    Args:
        session: 数据库会话
        agent: Agent实例
        dry_run: 是否只是测试模式

    Returns:
        是否成功迁移
    """
    if not agent.prompt:
        logger.info(f"Agent {agent.name} 没有prompt，跳过")
        return False

    # 检查是否已有角色卡信息
    if agent.personality or agent.scenario:
        logger.info(f"Agent {agent.name} 已有角色卡信息，跳过")
        return False

    # 分析prompt内容
    character_data = analyze_prompt_content(agent.prompt)

    logger.info(f"\n=== Agent: {agent.name} ===")
    logger.info(f"原prompt长度: {len(agent.prompt)}字符")
    logger.info(f"提取的personality: {character_data['personality'][:100]}...")
    logger.info(f"提取的scenario: {character_data['scenario'][:100]}...")

    if not dry_run:
        # 更新数据库
        agent.personality = character_data["personality"]
        agent.scenario = character_data["scenario"]
        agent.message_example = character_data["message_example"]
        agent.creator_notes = character_data["creator_notes"]

        # 保留原prompt在creator_notes中作为备份
        if character_data["creator_notes"]:
            agent.creator_notes += f"\n\n原始prompt:\n{agent.prompt[:200]}..."

        session.add(agent)
        logger.info(f"已更新Agent {agent.name}的角色卡信息")

    return True


async def migrate_all_agents(dry_run: bool = True):
    """
    迁移所有Agent的prompt到角色卡字段

    Args:
        dry_run: 是否只是测试模式，不实际修改数据库
    """
    logger.info(f"开始迁移Agent prompt到角色卡字段 (dry_run={dry_run})")

    # 获取数据库会话
    async for session in get_async_db():
        try:
            # 查询所有有prompt但没有角色卡信息的Agent
            from sqlalchemy import select

            result = await session.execute(
                select(models.Agent).where(
                    models.Agent.deleted_at.is_(None),
                    models.Agent.prompt.isnot(None),
                    models.Agent.prompt != "",
                    # 至少一个角色卡字段为空
                    (
                        models.Agent.personality.is_(None)
                        | (models.Agent.personality == "")
                        | models.Agent.scenario.is_(None)
                        | (models.Agent.scenario == "")
                    ),
                )
            )
            agents = result.scalars().all()

            logger.info(f"找到 {len(agents)} 个需要迁移的Agent")

            success_count = 0
            for agent in agents:
                try:
                    if await migrate_single_agent(session, agent, dry_run):
                        success_count += 1
                except Exception as e:
                    logger.error(f"迁移Agent {agent.name} 失败: {str(e)}")

            if not dry_run:
                await session.commit()
                logger.info(f"成功迁移 {success_count} 个Agent的prompt到角色卡字段")
            else:
                logger.info(f"测试模式：预计可迁移 {success_count} 个Agent")

        except Exception as e:
            if not dry_run:
                await session.rollback()
            logger.error(f"迁移过程出错: {str(e)}")
            raise
        finally:
            break  # 只需要一个数据库会话


async def main():
    """主函数"""
    print("Agent Prompt 迁移工具")
    print("=" * 50)
    print("1. 测试模式 (预览迁移效果)")
    print("2. 执行迁移")
    print("3. 退出")

    choice = input("请选择操作 (1-3): ").strip()

    if choice == "1":
        await migrate_all_agents(dry_run=True)
    elif choice == "2":
        confirm = input("确认要执行迁移吗？这将修改数据库 (y/N): ").strip().lower()
        if confirm == "y":
            await migrate_all_agents(dry_run=False)
        else:
            print("取消迁移")
    else:
        print("退出")


if __name__ == "__main__":
    asyncio.run(main())
