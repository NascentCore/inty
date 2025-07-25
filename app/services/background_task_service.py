import asyncio
import json
import time
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import threading
import logging

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
                target=self._worker_loop,
                name=f"BackgroundWorker-{i}",
                daemon=True
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
                    task_type = task.get('type')
                    task_data = task.get('data')
                    
                    if task_type == 'debug_save':
                        self._handle_debug_save_task(task_data)
                    else:
                        logger.warning(f"未知任务类型: {task_type}")
                
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
    
    def submit_debug_save_task(self, user_id: str, session_id: str, agent_id: str, debug_data: dict):
        """提交调试信息保存任务"""
        if not self.running:
            logger.warning("后台任务服务未启动，跳过调试信息保存")
            return
        
        task = {
            'type': 'debug_save',
            'data': {
                'user_id': user_id,
                'session_id': session_id,
                'agent_id': agent_id,
                'debug_data': debug_data,
                'timestamp': time.time()
            }
        }
        
        try:
            self.task_queue.put(task, timeout=1.0)
            logger.debug(f"提交调试保存任务: Agent={agent_id}, User={user_id}")
        except Exception as e:
            logger.error(f"提交调试保存任务失败: {str(e)}")
    
    def _handle_debug_save_task(self, task_data: dict):
        """处理调试信息保存任务"""
        user_id = task_data['user_id']
        session_id = task_data['session_id']
        agent_id = task_data['agent_id']
        debug_data = task_data['debug_data']
        
        try:
            start_time = time.time()
            
            # 使用独立的数据库连接进行保存
            from app.core.agent.agent import get_connection_pool
            
            pool = get_connection_pool()
            with pool.connection() as conn:
                self._save_debug_messages_to_db(
                    user_id, session_id, agent_id, debug_data, conn
                )
            
            elapsed = time.time() - start_time
            logger.debug(f"后台调试信息保存完成: Agent={agent_id}, 耗时={elapsed:.3f}秒")
            
        except Exception as e:
            logger.error(f"后台调试信息保存失败: Agent={agent_id}, Error={str(e)}")
    
    def _save_debug_messages_to_db(self, user_id: str, session_id: str, agent_id: str, debug_data: dict, conn):
        """保存调试信息到数据库（在后台线程中执行）"""
        try:
            # 优先使用预格式化的消息，确保与同步版本一致
            if "formatted_messages" in debug_data:
                # 使用agent.py中预处理的完整消息链（包含动态提示词）
                messages = debug_data["formatted_messages"]
                logger.debug(f"使用预格式化消息，共{len(messages)}条消息")
            else:
                # 回退到旧的逻辑（向后兼容）
                logger.warning(f"未找到预格式化消息，使用回退逻辑 - Agent: {agent_id}")
                messages = []
                
                # 处理输入数据
                input_data = debug_data.get("input_data", {})
                
                try:
                    # 简化的消息构建逻辑，避免复杂的提示词处理
                    system_messages = input_data.get("messages", [])
                    
                    for msg in system_messages:
                        if hasattr(msg, 'type') and hasattr(msg, 'content'):
                            msg_type = msg.type
                            if msg_type == 'human':
                                msg_type = 'user'
                            elif msg_type == 'ai':
                                msg_type = 'character'
                            messages.append({"type": msg_type, "content": msg.content})
                        elif isinstance(msg, dict):
                            msg_type = msg.get('type', 'system')
                            if msg_type == 'human':
                                msg_type = 'user'
                            elif msg_type == 'ai':
                                msg_type = 'character'
                            messages.append({"type": msg_type, "content": msg.get('content', '')})
                            
                except Exception as e:
                    logger.error(f"构建调试消息链失败: {str(e)}")
                    # 使用fallback消息
                    messages = [{"type": "system", "content": "调试消息构建失败"}]
                
                # 添加AI响应消息（只在回退逻辑中需要，预格式化消息已包含）
                response_text = debug_data.get("response_text", "")
                if response_text:
                    messages.append({"type": "character", "content": response_text})
            
            # 保存到数据库
            debug_data_to_save = {
                "messages": messages,
                "timestamp": time.time(),
                "agent_id": agent_id,
                "user_id": user_id,
                "session_id": session_id
            }
            
            query = """
                UPDATE chats 
                SET debug_messages = %s, updated_at = now()
                WHERE user_id = %s AND agent_id = %s AND is_active = true
            """
            
            with conn.cursor() as cursor:
                cursor.execute(query, (json.dumps(debug_data_to_save), user_id, agent_id))
                rows_affected = cursor.rowcount
                conn.commit()
            
            logger.debug(f"后台调试信息保存成功: Agent={agent_id}, 消息数={len(messages)}, 影响行数={rows_affected}")
            
        except Exception as e:
            logger.error(f"后台调试信息保存到数据库失败: Agent={agent_id}, Error={str(e)}")
    
    def get_queue_size(self) -> int:
        """获取当前队列大小"""
        return self.task_queue.qsize()
    
    def get_stats(self) -> dict:
        """获取服务统计信息"""
        return {
            'running': self.running,
            'max_workers': self.max_workers,
            'active_threads': len([t for t in self.worker_threads if t.is_alive()]),
            'queue_size': self.get_queue_size()
        }


# 全局后台任务服务实例
background_task_service = BackgroundTaskService()