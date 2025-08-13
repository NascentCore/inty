import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue

logger = logging.getLogger(__name__)


class BackgroundTaskService:
    """后台任务服务"""

    def __init__(self, max_workers: int = 20):
        self.max_workers = max_workers
        self.executor = None
        self.task_queue = Queue()
        self.worker_threads = []
        self.shutdown_event = threading.Event()
        self.running = False

    def start(self):
        """启动后台任务服务"""
        if self.running:
            return

        self.running = True
        self.shutdown_event.clear()

        # 创建线程池
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

        # 启动工作线程
        for i in range(self.max_workers):
            worker_thread = threading.Thread(
                target=self._worker_loop, name=f"BackgroundWorker-{i}", daemon=True
            )
            worker_thread.start()
            self.worker_threads.append(worker_thread)

        logger.info(f"后台任务服务已启动，工作线程数: {self.max_workers}")

    def stop(self):
        """停止后台任务服务"""
        if not self.running:
            return

        logger.info("正在停止后台任务服务...")

        # 设置停止标志
        self.running = False
        self.shutdown_event.set()

        # 向队列发送停止信号
        for _ in range(self.max_workers):
            self.task_queue.put(None)

        # 等待工作线程结束
        for thread in self.worker_threads:
            thread.join(timeout=5.0)

        # 关闭线程池
        if self.executor:
            self.executor.shutdown(wait=True, timeout=10.0)

        self.worker_threads.clear()
        logger.info("后台任务服务已停止")

    def _worker_loop(self):
        """工作线程主循环"""
        thread_name = threading.current_thread().name
        logger.debug(f"后台工作线程启动: {thread_name}")

        while self.running:
            try:
                # 从队列获取任务
                task = self.task_queue.get(timeout=1.0)

                # None是停止信号
                if task is None:
                    break

                # 执行任务
                try:
                    task_type = task.get("type")
                    task_data = task.get("data")
                    # Add your task execution logic here.
                    logger.debug(f"执行后台任务: {task_type} - {task_data}")
                except Exception as e:
                    logger.error(f"执行后台任务失败: {str(e)}")

                # 标记任务完成
                self.task_queue.task_done()

            except Empty:
                # 队列超时，继续循环
                continue
            except Exception as e:
                logger.error(f"后台工作线程异常: {str(e)}")

        logger.debug(f"后台工作线程结束: {thread_name}")

    def get_queue_size(self) -> int:
        """获取当前队列大小"""
        return self.task_queue.qsize()

    def get_stats(self) -> dict:
        """获取服务统计信息"""
        return {
            "running": self.running,
            "max_workers": self.max_workers,
            "active_threads": len([t for t in self.worker_threads if t.is_alive()]),
            "queue_size": self.get_queue_size(),
        }


# 全局后台任务服务实例
background_task_service = BackgroundTaskService()
