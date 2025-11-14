"""
推送服务独立入口

独立的服务入口，可单独运行，用于处理推送通知任务。
"""

import asyncio
import signal
import sys
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent.agent import agent_manager
from app.core.config import global_config_loaded_from_config_yaml
from app.core.logging import init_logger
from app.db.session import AsyncSessionLocal
from app.external_services.firebase import init_firebase
from app.services import agent_service
from app.services.push_scheduler_service import push_scheduler_service


class PushWorker:
    """推送服务工作者"""

    def __init__(self):
        self.is_running = False
        self.shutdown_event: Optional[asyncio.Event] = None

    async def initialize(self) -> None:
        """初始化服务依赖"""
        try:
            logger.info("正在初始化推送服务...")

            # 初始化日志
            init_logger()

            # 初始化 Firebase
            try:
                init_firebase()
                logger.info("Firebase 初始化成功")
            except Exception as e:
                logger.warning(f"Firebase 初始化失败（可能未配置）: {str(e)}")

            # 初始化数据库连接和 AgentManager
            async with AsyncSessionLocal() as db_session:
                try:
                    # 预加载热门 Agent 数据（如果方法存在）
                    logger.info("正在预加载 Agent 数据...")
                    if hasattr(agent_service, "preload_popular_agents"):
                        await agent_service.preload_popular_agents(db_session)

                    # 初始化 AgentManager
                    await agent_manager.initialize_popular_agents(db_session)
                    logger.info("AgentManager 初始化完成")

                except Exception as e:
                    logger.error(f"初始化 AgentManager 失败: {str(e)}")
                    raise

            logger.info("推送服务初始化完成")

        except Exception as e:
            logger.error(f"推送服务初始化失败: {str(e)}")
            raise

    def start(self) -> bool:
        """启动推送服务

        Returns:
            是否成功启动（如果服务未启用，返回 False）
        """
        if self.is_running:
            logger.warning("推送服务已在运行")
            return True

        try:
            # 检查配置
            config = global_config_loaded_from_config_yaml.push_notification
            if not config.enabled:
                logger.info("推送服务未启用，退出")
                return False

            # 启动调度器
            push_scheduler_service.start()
            self.is_running = True

            logger.info("推送服务启动成功")
            return True

        except Exception as e:
            logger.error(f"启动推送服务失败: {str(e)}")
            raise

    def stop(self) -> None:
        """停止推送服务"""
        if not self.is_running:
            return

        try:
            push_scheduler_service.stop()
            self.is_running = False
            logger.info("推送服务已停止")

        except Exception as e:
            logger.error(f"停止推送服务失败: {str(e)}")

    async def run(self) -> None:
        """运行推送服务（阻塞）"""
        try:
            # 初始化
            await self.initialize()

            # 启动服务
            started = self.start()

            # 如果服务未启用，直接返回
            if not started:
                return

            # 创建关闭事件
            self.shutdown_event = asyncio.Event()

            # 等待关闭信号
            try:
                await self.shutdown_event.wait()
            except asyncio.CancelledError:
                logger.info("推送服务被取消")
                raise

        except KeyboardInterrupt:
            logger.info("收到键盘中断信号")
        except asyncio.CancelledError:
            logger.info("推送服务被取消")
            raise
        except Exception as e:
            logger.error(f"推送服务运行失败: {str(e)}")
            raise
        finally:
            self.stop()


def setup_signal_handlers(worker: PushWorker, loop: asyncio.AbstractEventLoop) -> None:
    """设置信号处理器"""

    def signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}，准备关闭服务...")
        if worker.shutdown_event:
            # 在事件循环中设置事件
            loop.call_soon_threadsafe(worker.shutdown_event.set)
        else:
            # 如果事件还未创建，说明服务未运行，直接取消所有任务
            logger.info("服务未运行，取消所有任务")
            try:
                # 获取所有未完成的任务并取消
                tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
                for task in tasks:
                    task.cancel()
            except Exception as e:
                logger.warning(f"取消任务时出错: {e}")

    # 只在 Unix 系统上设置信号处理器（Windows 不支持 SIGTERM）
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def main() -> None:
    """主函数"""
    worker = PushWorker()
    loop = asyncio.get_event_loop()

    # 设置信号处理器
    setup_signal_handlers(worker, loop)

    try:
        # 运行服务
        await worker.run()
    except KeyboardInterrupt:
        logger.info("收到键盘中断，退出")
    except asyncio.CancelledError:
        logger.info("服务被取消，退出")
    except Exception as e:
        logger.error(f"推送服务异常退出: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
