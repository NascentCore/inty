#!/usr/bin/env python3
"""
从personality字段提取tags的主脚本

使用方法:
    python extract_tags_from_personality.py --analyze                    # 分析模式，只查看不更新
    python extract_tags_from_personality.py --update                     # 执行更新
    python extract_tags_from_personality.py --config ../config.yaml      # 指定配置文件
    python extract_tags_from_personality.py --batch-size 50 --update     # 指定批处理大小
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import click

# 导入自定义模块
from .database import create_database_manager, DatabaseManager
from .tag_parser import TagParser
from .logger import setup_logger, get_default_log_file, MigrationLogger
from .models import TagExtractionResult, MigrationStats, MigrationConfig


class TagMigrator:
    """标签迁移器主类"""

    def __init__(self, config_path: str, migration_config: MigrationConfig):
        self.config_path = config_path
        self.migration_config = migration_config
        self.db_manager: Optional[DatabaseManager] = None
        self.tag_parser = TagParser()
        self.logger = None
        self.migration_logger = None

    async def initialize(self):
        """初始化迁移器"""
        # 设置日志
        log_file = self.migration_config.log_file or get_default_log_file()
        self.logger = setup_logger(
            level=self.migration_config.log_level, log_file=log_file
        )
        self.migration_logger = MigrationLogger(self.logger)

        # 初始化数据库
        self.db_manager = await create_database_manager(self.config_path)

        # 测试数据库连接
        if not await self.db_manager.test_connection():
            raise ConnectionError("数据库连接测试失败")

        self.logger.info("迁移器初始化完成")

    async def close(self):
        """关闭迁移器"""
        if self.db_manager:
            await self.db_manager.close()

    async def analyze_agents(self) -> MigrationStats:
        """
        分析智能体数据，不进行实际更新

        Returns:
            迁移统计信息
        """
        self.logger.info("开始分析智能体数据...")

        start_time = time.time()
        stats = MigrationStats()

        # 获取数据库统计信息
        db_stats = await self.db_manager.get_database_stats()
        self.logger.info(f"数据库统计信息: {db_stats}")

        # 获取包含personality的智能体
        total_count = await self.db_manager.count_agents_with_personality()
        stats.total_agents = total_count
        stats.agents_with_personality = total_count

        self.logger.info(f"找到 {total_count} 个包含personality字段的智能体")
        self.migration_logger.set_progress_total(total_count)

        # 分批处理
        batch_size = self.migration_config.batch_size
        offset = 0
        all_results: List[TagExtractionResult] = []

        while offset < total_count:
            agents = await self.db_manager.get_agents_with_personality(
                limit=batch_size, offset=offset
            )

            if not agents:
                break

            # 处理当前批次
            batch_results = await self._process_batch_analysis(agents)
            all_results.extend(batch_results)

            offset += len(agents)
            self.migration_logger.log_progress(f"已分析 {len(agents)} 个智能体")

        # 生成统计信息
        stats = self._generate_stats(all_results)
        stats.execution_time_seconds = time.time() - start_time

        # 记录详细统计
        self.migration_logger.log_stats(stats.model_dump())

        return stats

    async def migrate_tags(self) -> MigrationStats:
        """
        执行标签迁移

        Returns:
            迁移统计信息
        """
        if self.migration_config.dry_run:
            self.logger.warning("当前为试运行模式，不会实际更新数据库")
            return await self.analyze_agents()

        self.logger.info("开始执行标签迁移...")

        start_time = time.time()
        stats = MigrationStats()

        # 获取包含personality的智能体
        total_count = await self.db_manager.count_agents_with_personality()
        stats.total_agents = total_count
        stats.agents_with_personality = total_count

        self.logger.info(f"准备迁移 {total_count} 个智能体的标签")
        self.migration_logger.set_progress_total(total_count)

        # 分批处理
        batch_size = self.migration_config.batch_size
        offset = 0
        all_results: List[TagExtractionResult] = []

        while offset < total_count:
            agents = await self.db_manager.get_agents_with_personality(
                limit=batch_size, offset=offset
            )

            if not agents:
                break

            # 备份当前批次数据
            if self.migration_config.backup_before_update:
                backup_data = await self.db_manager.backup_agents_data(
                    [a.id for a in agents]
                )
                await self._save_backup(backup_data, offset // batch_size)

            # 处理当前批次
            batch_results = await self._process_batch_migration(agents)
            all_results.extend(batch_results)

            offset += len(agents)
            self.migration_logger.log_progress(f"已处理 {len(agents)} 个智能体")

        # 生成统计信息
        stats = self._generate_stats(all_results)
        stats.execution_time_seconds = time.time() - start_time

        # 记录详细统计
        self.migration_logger.log_stats(stats.model_dump())

        return stats

    async def _process_batch_analysis(
        self, agents
    ) -> List[TagExtractionResult]:
        """处理一批智能体的分析"""
        results = []

        for agent in agents:
            # 提取标签
            result = self.tag_parser.extract_tags_from_personality(
                agent.personality, agent.id, agent.name
            )

            # 检查是否需要跳过已有标签的智能体
            if (
                self.migration_config.skip_existing_tags
                and agent.tags
                and len(agent.tags) > 0
            ):
                result.error_message = "智能体已有标签，跳过处理"
                self.migration_logger.log_extraction_failure(
                    agent.name, result.error_message
                )
            elif result.extraction_success:
                # 标准化标签
                if self.migration_config.normalize_tags:
                    result.extracted_tags = self.tag_parser.normalize_tags(
                        result.extracted_tags
                    )

                # 验证标签
                valid_tags, invalid_tags = self.tag_parser.validate_tags(
                    result.extracted_tags
                )
                if invalid_tags:
                    self.logger.warning(
                        f"{agent.name}: 发现无效标签: {invalid_tags}"
                    )

                result.extracted_tags = valid_tags
                result.original_tags = agent.tags

                if valid_tags:
                    self.migration_logger.log_extraction_success(
                        agent.name, valid_tags, result.extraction_method
                    )
                else:
                    result.extraction_success = False
                    result.error_message = "没有有效的标签"
            else:
                self.migration_logger.log_extraction_failure(
                    agent.name, result.error_message
                )

            results.append(result)

        return results

    async def _process_batch_migration(
        self, agents
    ) -> List[TagExtractionResult]:
        """处理一批智能体的迁移"""
        results = await self._process_batch_analysis(agents)

        # 准备更新数据
        updates = []
        for result in results:
            if (
                result.extraction_success
                and result.extracted_tags
                and not (
                    result.error_message
                    and result.error_message.startswith("智能体已有标签")
                )
            ):
                updates.append((result.agent_id, result.extracted_tags))

        # 批量更新数据库
        if updates:
            success_count, _ = await self.db_manager.batch_update_agent_tags(
                updates
            )

            # 更新统计信息
            for i, (agent_id, tags) in enumerate(updates):
                result = next(r for r in results if r.agent_id == agent_id)
                agent_name = result.agent_name

                if i < success_count:
                    self.migration_logger.log_update_success(agent_name, tags)
                else:
                    self.migration_logger.log_update_failure(
                        agent_name, "数据库更新失败"
                    )
                    result.error_message = "数据库更新失败"
                    result.extraction_success = False

        return results

    def _generate_stats(
        self, results: List[TagExtractionResult]
    ) -> MigrationStats:
        """生成迁移统计信息"""
        stats = MigrationStats()

        stats.total_agents = len(results)
        stats.agents_with_personality = len(results)

        # 统计提取成功和失败
        successful_results = [r for r in results if r.extraction_success]
        stats.successful_extractions = len(successful_results)
        stats.failed_extractions = len(results) - len(successful_results)

        # 统计有Character info的智能体
        stats.agents_with_character_info = len(
            [r for r in results if r.character_info]
        )

        # 统计可提取标签的智能体
        stats.agents_with_extractable_tags = len(
            [r for r in results if r.character_info and r.character_info.tags]
        )

        # 统计更新成功的智能体
        stats.updated_agents = len(
            [r for r in successful_results if r.extracted_tags]
        )

        # 统计跳过的智能体
        stats.skipped_agents = len(
            [
                r
                for r in results
                if r.error_message and "跳过" in r.error_message
            ]
        )

        # 统计最常见的标签
        all_tags = []
        for result in successful_results:
            all_tags.extend(result.extracted_tags)

        from collections import Counter

        tag_counter = Counter(all_tags)
        stats.most_common_tags = dict(tag_counter.most_common(20))

        return stats

    async def _save_backup(
        self, backup_data: List[Dict[str, Any]], batch_number: int
    ):
        """保存备份数据"""
        if not backup_data:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_batch_{batch_number}_{timestamp}.json"
        backup_path = Path(backup_file)

        try:
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(
                    backup_data, f, ensure_ascii=False, indent=2, default=str
                )

            self.logger.info(f"备份数据已保存: {backup_path}")
        except Exception as e:
            self.logger.error(f"保存备份失败: {e}")


# CLI命令定义
@click.command()
@click.option(
    "--config",
    "-c",
    default="../../config.yaml",
    help="配置文件路径",
    type=click.Path(exists=True),
)
@click.option(
    "--analyze", is_flag=True, help="分析模式：只分析数据，不进行更新"
)
@click.option("--update", is_flag=True, help="更新模式：执行实际的标签迁移")
@click.option("--batch-size", default=100, help="批处理大小", type=int)
@click.option(
    "--skip-existing", is_flag=True, default=True, help="跳过已有标签的智能体"
)
@click.option("--normalize", is_flag=True, default=True, help="标准化标签")
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="日志级别",
)
@click.option("--log-file", help="日志文件路径")
def main(
    config,
    analyze,
    update,
    batch_size,
    skip_existing,
    normalize,
    log_level,
    log_file,
):
    """
    从personality字段提取tags的迁移工具

    示例:
        python extract_tags_from_personality.py --analyze
        python extract_tags_from_personality.py --update --batch-size 50
    """
    # 验证参数
    if not analyze and not update:
        click.echo("错误: 必须指定 --analyze 或 --update 模式", err=True)
        sys.exit(1)

    if analyze and update:
        click.echo("错误: --analyze 和 --update 不能同时使用", err=True)
        sys.exit(1)

    # 创建迁移配置
    migration_config = MigrationConfig(
        batch_size=batch_size,
        dry_run=analyze,
        skip_existing_tags=skip_existing,
        normalize_tags=normalize,
        log_level=log_level,
        log_file=log_file,
    )

    # 运行迁移
    asyncio.run(run_migration(config, migration_config, analyze))


async def run_migration(
    config_path: str, migration_config: MigrationConfig, analyze_only: bool
):
    """运行迁移流程"""
    migrator = TagMigrator(config_path, migration_config)

    try:
        await migrator.initialize()

        if analyze_only:
            click.echo("=== 分析模式 ===")
            stats = await migrator.analyze_agents()
        else:
            click.echo("=== 迁移模式 ===")
            stats = await migrator.migrate_tags()

        # 显示最终统计
        click.echo("\n" + "=" * 50)
        click.echo("迁移完成！统计信息:")
        click.echo(f"  总智能体数: {stats.total_agents}")
        click.echo(f"  成功提取: {stats.successful_extractions}")
        click.echo(f"  提取失败: {stats.failed_extractions}")
        if not analyze_only:
            click.echo(f"  更新成功: {stats.updated_agents}")
            click.echo(f"  跳过处理: {stats.skipped_agents}")

        if stats.execution_time_seconds:
            click.echo(f"  执行时间: {stats.execution_time_seconds:.2f} 秒")

        if stats.most_common_tags:
            click.echo("\n最常见的标签:")
            for tag, count in list(stats.most_common_tags.items())[:10]:
                click.echo(f"  {tag}: {count}")

        click.echo("=" * 50)

    except Exception as e:
        click.echo(f"迁移失败: {e}", err=True)
        sys.exit(1)
    finally:
        await migrator.close()


if __name__ == "__main__":
    main()
