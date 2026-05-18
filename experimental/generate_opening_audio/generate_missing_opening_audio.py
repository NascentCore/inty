#!/usr/bin/env python3
"""
批量为 opening_audio_url 为空的 agents 生成开场白语音

使用示例：
    # 查看有多少 agents 需要生成语音（dry-run）
    python generate_missing_opening_audio.py --dry-run

    # 生成所有缺失的开场白语音
    python generate_missing_opening_audio.py

    # 只处理前 5 个 agents（测试用）
    python generate_missing_opening_audio.py --limit 5

    # 为指定 agent 生成语音
    python generate_missing_opening_audio.py --agent-id <agent-id>
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import yaml
from loguru import logger
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.models.agent import Agent
from app.services.voice_service import VoiceService, GENDER_VOICE_MAPPING
from app.core.agent.prompt_template import (
    has_template_variable,
    render_prompt_jinja2_template,
)


class OpeningAudioGenerator:
    """开场白语音生成器"""

    def __init__(
        self, config_path: str, dry_run: bool = False, batch_size: int = 10
    ):
        self.config_path = config_path
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.config = None
        self.engine = None
        self.async_session = None
        self.voice_service = None

        # 统计信息
        self.stats = {
            "total": 0,
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }

    def load_config(self):
        """从 YAML 文件加载配置"""
        logger.info(f"加载配置文件: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        logger.info("配置加载成功")

    async def setup_database(self):
        """设置数据库连接"""
        db_config = self.config["database"]
        async_url = f"postgresql+asyncpg://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['db']}"

        logger.info(
            f"连接数据库: {db_config['host']}:{db_config['port']}/{db_config['db']}"
        )

        self.engine = create_async_engine(
            async_url,
            pool_size=db_config.get("pool_size", 10),
            max_overflow=db_config.get("max_overflow", 5),
            pool_timeout=db_config.get("pool_timeout", 10),
            pool_recycle=db_config.get("pool_recycle", 3600),
            pool_pre_ping=db_config.get("pool_pre_ping", True),
        )

        self.async_session = sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

        logger.info("数据库连接建立成功")

    async def setup_voice_service(self):
        """设置语音服务"""
        # 由于 VoiceService 需要从 global_config 读取配置
        # 我们需要在这里临时设置环境变量或直接初始化
        # 这里直接创建实例，它会从 global_config 读取
        from app.core.config import global_config_loaded_from_config_yaml

        # 验证 ElevenLabs 配置是否可用
        if not global_config_loaded_from_config_yaml.elevenlabs.enabled:
            logger.warning("ElevenLabs 语音生成未启用")
        else:
            logger.info("ElevenLabs 语音服务已启用")

        self.voice_service = VoiceService()

    async def get_agents_without_audio(
        self, limit: Optional[int] = None, agent_id: Optional[str] = None
    ) -> List[Agent]:
        """查询需要生成语音的 agents"""
        async with self.async_session() as session:
            query = (
                select(Agent)
                .where(
                    and_(
                        Agent.deleted_at.is_(None),  # 未删除
                        Agent.opening.isnot(None),  # 有开场白文本
                        Agent.opening != "",  # 开场白不为空
                        Agent.opening_audio_url.is_(None),  # 没有语音 URL
                    )
                )
                .order_by(Agent.created_at.desc())
            )

            # 如果指定了 agent_id，只查询该 agent
            if agent_id:
                query = query.where(Agent.id == agent_id)

            # 如果指定了 limit，限制查询数量
            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            agents = result.scalars().all()

            return list(agents)

    async def count_agents_without_audio(self) -> int:
        """统计需要生成语音的 agents 数量"""
        async with self.async_session() as session:
            query = select(func.count(Agent.id)).where(
                and_(
                    Agent.deleted_at.is_(None),
                    Agent.opening.isnot(None),
                    Agent.opening != "",
                    Agent.opening_audio_url.is_(None),
                )
            )
            result = await session.execute(query)
            return result.scalar()

    async def generate_opening_voice_for_agent(
        self, agent: Agent, session: AsyncSession
    ) -> bool:
        """为单个 agent 生成开场白语音"""
        try:
            if not agent.opening or not agent.opening.strip():
                logger.debug(
                    f"Agent {agent.id} ({agent.name}) 没有开场白文本，跳过"
                )
                self.stats["skipped"] += 1
                return False

            opening = agent.opening

            # 处理模板变量
            if has_template_variable(opening):
                opening = render_prompt_jinja2_template(
                    opening, char=agent.name, user="you"
                )
                logger.debug(
                    f"Agent {agent.id} 开场白包含模板变量，渲染后: {opening[:50]}..."
                )

            # 确定使用的 voice_id
            voice_id_to_use = agent.voice_id
            if not voice_id_to_use:
                voice_id_to_use = GENDER_VOICE_MAPPING.get(agent.gender.value)
                if not voice_id_to_use:
                    logger.warning(
                        f"Agent {agent.id} ({agent.name}) 性别 {agent.gender.value} 没有对应的默认音色ID，跳过"
                    )
                    self.stats["skipped"] += 1
                    return False

            logger.info(
                f"开始为 Agent {agent.id} ({agent.name}) 生成语音 "
                f"[voice_id: {voice_id_to_use}, text_length: {len(opening)}]"
            )

            # 生成语音
            voice_result = await self.voice_service.generate_voice(
                text=opening,
                voice_id=voice_id_to_use,
                db=session,  # 传入 session 以使用缓存
            )

            if not voice_result:
                logger.error(f"Agent {agent.id} ({agent.name}) 语音生成失败")
                self.stats["failed"] += 1
                return False

            audio_url, audio_duration = voice_result

            # 如果不是 dry-run，更新数据库
            if not self.dry_run:
                agent.opening_audio_url = audio_url
                session.add(agent)
                await session.commit()
                logger.info(
                    f"✓ Agent {agent.id} ({agent.name}) 语音生成成功: {audio_url} "
                    f"[时长: {audio_duration:.2f}秒]"
                )
            else:
                logger.info(
                    f"[DRY-RUN] Agent {agent.id} ({agent.name}) 语音生成成功: {audio_url} "
                    f"[时长: {audio_duration:.2f}秒] (未保存到数据库)"
                )

            self.stats["success"] += 1
            return True

        except Exception as e:
            logger.error(f"Agent {agent.id} ({agent.name}) 处理失败: {str(e)}")
            logger.exception("详细错误信息:")
            self.stats["failed"] += 1
            return False

    async def process_batch(self, agents: List[Agent]):
        """批量处理 agents"""
        async with self.async_session() as session:
            for i, agent in enumerate(agents, 1):
                logger.info(
                    f"[{i}/{len(agents)}] 处理 Agent {agent.id} ({agent.name})"
                )
                self.stats["processed"] += 1
                await self.generate_opening_voice_for_agent(agent, session)

    async def run(
        self, limit: Optional[int] = None, agent_id: Optional[str] = None
    ):
        """运行主逻辑"""
        start_time = datetime.now()

        logger.info("=" * 60)
        logger.info("开场白语音批量生成工具")
        logger.info("=" * 60)

        if self.dry_run:
            logger.warning("⚠️  DRY-RUN 模式：只查询和生成语音，不更新数据库")

        # 加载配置
        self.load_config()

        # 设置数据库连接
        await self.setup_database()

        # 设置语音服务
        await self.setup_voice_service()

        # 统计需要处理的 agents 数量
        if agent_id:
            logger.info(f"指定 Agent ID: {agent_id}")
        else:
            total_count = await self.count_agents_without_audio()
            self.stats["total"] = total_count
            logger.info(f"找到 {total_count} 个需要生成语音的 Agents")

            if total_count == 0:
                logger.info("✓ 所有 agents 的开场白语音都已生成")
                return

            if limit:
                logger.info(f"限制处理数量: {limit}")

        # 查询需要处理的 agents
        agents = await self.get_agents_without_audio(
            limit=limit, agent_id=agent_id
        )

        if not agents:
            logger.info("没有找到需要处理的 Agents")
            return

        logger.info(f"本次将处理 {len(agents)} 个 Agents")
        logger.info("-" * 60)

        # 批量处理
        batch_count = (len(agents) + self.batch_size - 1) // self.batch_size

        for batch_idx in range(batch_count):
            start_idx = batch_idx * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(agents))
            batch = agents[start_idx:end_idx]

            logger.info(
                f"\n批次 {batch_idx + 1}/{batch_count}: 处理 {len(batch)} 个 Agents"
            )
            logger.info("-" * 60)

            await self.process_batch(batch)

        # 输出统计信息
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("\n" + "=" * 60)
        logger.info("处理完成！统计信息：")
        logger.info(f"  总数: {self.stats['total']}")
        logger.info(f"  已处理: {self.stats['processed']}")
        logger.info(f"  成功: {self.stats['success']}")
        logger.info(f"  失败: {self.stats['failed']}")
        logger.info(f"  跳过: {self.stats['skipped']}")
        logger.info(f"  耗时: {duration:.2f} 秒")
        logger.info("=" * 60)

        # 关闭数据库连接
        if self.engine:
            await self.engine.dispose()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="批量为 opening_audio_url 为空的 agents 生成开场白语音",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 查看有多少 agents 需要生成语音（dry-run）
  python generate_missing_opening_audio.py --dry-run

  # 生成所有缺失的开场白语音
  python generate_missing_opening_audio.py

  # 只处理前 5 个 agents（测试用）
  python generate_missing_opening_audio.py --limit 5

  # 为指定 agent 生成语音
  python generate_missing_opening_audio.py --agent-id <agent-id>

  # 使用自定义配置文件
  python generate_missing_opening_audio.py --config /path/to/config.yaml
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="../../config.yaml",
        help="配置文件路径（默认：../../config.yaml）",
    )

    parser.add_argument(
        "--batch-size", type=int, default=10, help="每批处理的数量（默认：10）"
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="只查询和生成语音，不更新数据库"
    )

    parser.add_argument("--limit", type=int, help="限制处理的数量（用于测试）")

    parser.add_argument("--agent-id", type=str, help="只处理指定的 agent ID")

    args = parser.parse_args()

    # 配置日志
    logger.remove()  # 移除默认处理器
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )

    # 解析配置文件路径
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).parent / config_path

    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        sys.exit(1)

    # 创建生成器并运行
    generator = OpeningAudioGenerator(
        config_path=str(config_path),
        dry_run=args.dry_run,
        batch_size=args.batch_size,
    )

    try:
        await generator.run(limit=args.limit, agent_id=args.agent_id)
    except KeyboardInterrupt:
        logger.warning("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"运行失败: {str(e)}")
        logger.exception("详细错误信息:")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
