import asyncio
import logging
import time
from threading import RLock
from typing import Any, Dict, Optional

from loguru import logger


class InMemoryCache:
    """内存缓存实现（线程安全）"""

    def __init__(self, default_ttl: int = 300):  # 默认5分钟过期
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() < entry["expires_at"]:
                    logger.debug(f"缓存命中: {key}")
                    return entry["value"]
                else:
                    # 过期删除
                    del self._cache[key]
                    logger.debug(f"缓存过期删除: {key}")

            logger.debug(f"缓存未命中: {key}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl

        with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": time.time(),
            }
            logger.debug(f"缓存设置: {key}, TTL: {ttl}秒")

    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"缓存删除: {key}")
                return True
            return False

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"清空缓存，共删除 {count} 个条目")

    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []

        with self._lock:
            for key, entry in self._cache.items():
                if current_time >= entry["expires_at"]:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

        if expired_keys:
            logger.debug(f"清理过期缓存，删除 {len(expired_keys)} 个条目")

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            current_time = time.time()
            expired_count = sum(
                1
                for entry in self._cache.values()
                if current_time >= entry["expires_at"]
            )

            return {
                "total_entries": len(self._cache),
                "expired_entries": expired_count,
                "active_entries": len(self._cache) - expired_count,
            }


class CacheService:
    """缓存服务管理器"""

    def __init__(self):
        # 用户信息缓存（较长过期时间）
        self.user_cache = InMemoryCache(default_ttl=600)  # 10分钟
        # 会话信息缓存（较短过期时间）
        self.session_cache = InMemoryCache(default_ttl=300)  # 5分钟
        # Agent配置缓存
        self.agent_cache = InMemoryCache(default_ttl=1800)  # 30分钟

        self._cleanup_task = None
        self._cleanup_running = False
        self._cleanup_run_count = 0

    async def start_cleanup_task(self):
        """启动清理任务"""
        if self._cleanup_running:
            return

        self._cleanup_running = True

        async def cleanup_loop():
            while self._cleanup_running:
                try:
                    # 每2分钟清理一次过期缓存
                    await asyncio.sleep(120)

                    total_cleaned = 0
                    total_cleaned += self.user_cache.cleanup_expired()
                    total_cleaned += self.session_cache.cleanup_expired()
                    total_cleaned += self.agent_cache.cleanup_expired()

                    if total_cleaned > 0:
                        logger.debug(
                            f"定时清理过期缓存，共清理 {total_cleaned} 个条目"
                        )

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"缓存清理任务出错: {str(e)}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("缓存清理任务已启动")

    def stop_cleanup_task(self):
        """停止清理任务"""
        self._cleanup_running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("缓存清理任务已停止")

    def get_user_info(self, user_id: str) -> Optional[str]:
        """获取用户信息缓存"""
        return self.user_cache.get(f"user_info:{user_id}")

    def set_user_info(
        self, user_id: str, user_info: str, ttl: Optional[int] = None
    ) -> None:
        """设置用户信息缓存"""
        self.user_cache.set(f"user_info:{user_id}", user_info, ttl)

    def invalidate_user_info(self, user_id: str) -> bool:
        """清除用户信息缓存"""
        return self.user_cache.delete(f"user_info:{user_id}")

    def get_user_auth_snapshot(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取鉴权用户快照缓存"""
        return self.user_cache.get(f"user_auth_snapshot:{user_id}")

    def set_user_auth_snapshot(
        self, user_id: str, snapshot: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        """设置鉴权用户快照缓存"""
        self.user_cache.set(f"user_auth_snapshot:{user_id}", snapshot, ttl)

    def invalidate_user_auth_snapshot(self, user_id: str) -> bool:
        """清除鉴权用户快照缓存"""
        return self.user_cache.delete(f"user_auth_snapshot:{user_id}")

    def get_session_info(self, session_key: str) -> Optional[Dict[str, Any]]:
        """获取会话信息缓存"""
        return self.session_cache.get(f"session:{session_key}")

    def set_session_info(
        self,
        session_key: str,
        session_info: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """设置会话信息缓存"""
        self.session_cache.set(f"session:{session_key}", session_info, ttl)

    def invalidate_session_info(self, session_key: str) -> bool:
        """清除会话信息缓存"""
        return self.session_cache.delete(f"session:{session_key}")

    def get_agent_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取Agent配置缓存"""
        return self.agent_cache.get(f"agent_config:{agent_id}")

    def set_agent_config(
        self, agent_id: str, config: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        """设置Agent配置缓存"""
        self.agent_cache.set(f"agent_config:{agent_id}", config, ttl)

    def invalidate_agent_config(self, agent_id: str) -> bool:
        """清除Agent配置缓存"""
        return self.agent_cache.delete(f"agent_config:{agent_id}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取所有缓存统计信息"""
        return {
            "user_cache": self.user_cache.get_stats(),
            "session_cache": self.session_cache.get_stats(),
            "agent_cache": self.agent_cache.get_stats(),
            "cleanup_running": self._cleanup_running,
        }

    def clear_all_caches(self) -> None:
        """清空所有缓存"""
        self.user_cache.clear()
        self.session_cache.clear()
        self.agent_cache.clear()
        logger.info("所有缓存已清空")


# 全局缓存服务实例
cache_service = CacheService()
