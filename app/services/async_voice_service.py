"""
异步语音处理服务
实现文本响应和语音生成的完全解耦
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.voice_service import voice_service
from app.services.voice_cache_service import voice_cache_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class AsyncVoiceService:
    """异步语音处理服务"""
    
    def __init__(self):
        self.voice_service = voice_service
        self.cache_service = voice_cache_service
        self.pending_tasks = {}  # 存储待处理的语音任务
        
    async def generate_voice_async(
        self,
        message_id: str,
        text: str,
        voice_id: Optional[str] = None,
        language: str = "zh",
        db: Optional[AsyncSession] = None,
        callback_url: Optional[str] = None
    ) -> str:
        """
        异步生成语音，立即返回任务ID
        
        Args:
            message_id: 消息ID
            text: 文本内容
            voice_id: 语音ID
            language: 语言
            db: 数据库会话
            callback_url: 回调URL（可选）
            
        Returns:
            任务ID
        """
        task_id = f"voice_{message_id}_{asyncio.current_task().get_name()}"
        
        # 创建异步任务
        task = asyncio.create_task(
            self._generate_voice_task(
                task_id, text, voice_id, language, db, callback_url
            )
        )
        
        # 存储任务引用
        self.pending_tasks[task_id] = {
            "task": task,
            "message_id": message_id,
            "status": "pending",
            "created_at": asyncio.get_event_loop().time()
        }
        
        logger.info(f"异步语音生成任务已创建: {task_id}")
        return task_id
    
    async def _generate_voice_task(
        self,
        task_id: str,
        text: str,
        voice_id: Optional[str],
        language: str,
        db: Optional[AsyncSession],
        callback_url: Optional[str]
    ) -> None:
        """
        实际的语音生成任务
        """
        try:
            # 更新任务状态
            if task_id in self.pending_tasks:
                self.pending_tasks[task_id]["status"] = "processing"
            
            logger.info(f"开始处理异步语音任务: {task_id}")
            
            # 生成语音
            audio_url = await self.voice_service.generate_voice(
                text=text,
                voice_id=voice_id,
                language=language,
                db=db
            )
            
            # 更新任务状态
            if task_id in self.pending_tasks:
                self.pending_tasks[task_id]["status"] = "completed"
                self.pending_tasks[task_id]["audio_url"] = audio_url
                self.pending_tasks[task_id]["completed_at"] = asyncio.get_event_loop().time()
            
            logger.info(f"异步语音任务完成: {task_id}, URL: {audio_url}")
            
            # 如果有回调URL，发送通知
            if callback_url and audio_url:
                await self._send_callback_notification(
                    callback_url, task_id, audio_url
                )
            
        except Exception as e:
            logger.error(f"异步语音任务失败: {task_id}, 错误: {str(e)}")
            
            # 更新任务状态
            if task_id in self.pending_tasks:
                self.pending_tasks[task_id]["status"] = "failed"
                self.pending_tasks[task_id]["error"] = str(e)
        
        finally:
            # 清理任务（可选，也可以保留一段时间供查询）
            await asyncio.sleep(300)  # 5分钟后清理
            if task_id in self.pending_tasks:
                del self.pending_tasks[task_id]
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        if task_id not in self.pending_tasks:
            return {"status": "not_found"}
        
        task_info = self.pending_tasks[task_id].copy()
        # 移除不需要序列化的任务对象
        task_info.pop("task", None)
        
        return task_info
    
    async def _send_callback_notification(
        self,
        callback_url: str,
        task_id: str,
        audio_url: str
    ) -> None:
        """
        发送回调通知
        """
        try:
            import aiohttp
            
            payload = {
                "task_id": task_id,
                "status": "completed",
                "audio_url": audio_url
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    callback_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        logger.info(f"回调通知发送成功: {task_id}")
                    else:
                        logger.warning(f"回调通知发送失败: {task_id}, 状态码: {response.status}")
        
        except Exception as e:
            logger.error(f"发送回调通知异常: {task_id}, 错误: {str(e)}")
    
    async def check_cache_first(
        self,
        text: str,
        voice_id: Optional[str] = None,
        language: str = "zh",
        db: Optional[AsyncSession] = None
    ) -> Optional[str]:
        """
        优先检查缓存，快速返回已存在的语音
        
        Args:
            text: 文本内容
            voice_id: 语音ID
            language: 语言
            db: 数据库会话
            
        Returns:
            缓存的语音URL，如果不存在则返回None
        """
        if not db:
            return None
        
        try:
            # 使用默认语音ID
            voice_id = voice_id or settings.elevenlabs.voice_id
            model = settings.elevenlabs.model
            
            # 快速检查缓存
            cached_url = await self.cache_service.get_cached_voice(
                db, text, voice_id, model, language
            )
            
            if cached_url:
                logger.info(f"快速缓存命中: {cached_url}")
                # 异步更新访问统计
                asyncio.create_task(
                    self.cache_service.update_access_stats(
                        db, text, voice_id, model, language
                    )
                )
                return cached_url
            
            return None
            
        except Exception as e:
            logger.error(f"缓存检查失败: {str(e)}")
            return None
    
    def get_active_tasks_count(self) -> int:
        """获取活跃任务数量"""
        return len(self.pending_tasks)
    
    def get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        stats = {
            "total_tasks": len(self.pending_tasks),
            "status_breakdown": {},
            "avg_processing_time": 0
        }
        
        # 统计状态分布
        for task_info in self.pending_tasks.values():
            status = task_info["status"]
            stats["status_breakdown"][status] = stats["status_breakdown"].get(status, 0) + 1
        
        # 计算平均处理时间（已完成的任务）
        completed_tasks = [
            task for task in self.pending_tasks.values() 
            if task["status"] == "completed" and "completed_at" in task
        ]
        
        if completed_tasks:
            total_time = sum(
                task["completed_at"] - task["created_at"] 
                for task in completed_tasks
            )
            stats["avg_processing_time"] = total_time / len(completed_tasks)
        
        return stats


# 创建全局实例
async_voice_service = AsyncVoiceService()