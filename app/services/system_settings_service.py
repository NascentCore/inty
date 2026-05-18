import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.models.system_settings import SettingCategory, SystemSettings
from app.services.cache_service import InMemoryCache

from loguru import logger


class SystemSettingsService:
    """系统配置服务"""

    def __init__(self):
        # 使用较长的缓存时间 (30分钟)
        self._cache = InMemoryCache(default_ttl=1800)
        self._cache_prefix = "system_setting:"

    def _get_cache_key(self, key: str) -> str:
        """生成缓存键"""
        return f"{self._cache_prefix}{key}"

    async def get_setting(
        self, db: AsyncSession, key: str, default_value: Optional[Any] = None
    ) -> Any:
        """
        获取系统配置值

        Args:
            db: 数据库会话
            key: 配置键名
            default_value: 默认值（如果配置不存在）

        Returns:
            解析后的配置值
        """
        try:
            # 先从缓存获取
            cache_key = self._get_cache_key(key)
            cached_value = self._cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 从数据库获取
            stmt = select(SystemSettings).where(SystemSettings.key == key)
            result = await db.execute(stmt)
            setting = result.scalar_one_or_none()

            if setting:
                parsed_value = setting.parsed_value
                # 缓存结果
                self._cache.set(cache_key, parsed_value)
                return parsed_value
            else:
                # 配置不存在，返回默认值
                if default_value is not None:
                    self._cache.set(cache_key, default_value)
                    return default_value

                logger.warning(f"系统配置不存在: {key}")
                return None

        except Exception as e:
            logger.error(f"获取系统配置失败 {key}: {str(e)}")
            return default_value

    async def set_setting(
        self,
        db: AsyncSession,
        key: str,
        value: Any,
        updated_by: Optional[str] = None,
    ) -> bool:
        """
        设置系统配置值

        Args:
            db: 数据库会话
            key: 配置键名
            value: 配置值
            updated_by: 更新者ID

        Returns:
            是否成功
        """
        try:
            # 查找现有配置
            stmt = select(SystemSettings).where(SystemSettings.key == key)
            result = await db.execute(stmt)
            setting = result.scalar_one_or_none()

            if setting:
                # 检查是否只读
                if setting.is_readonly:
                    logger.warning(f"尝试修改只读配置: {key}")
                    return False

                # 更新配置
                setting.value = str(value)
                setting.updated_by = updated_by
            else:
                logger.warning(f"配置不存在，无法更新: {key}")
                return False

            await db.commit()

            # 清除缓存
            cache_key = self._get_cache_key(key)
            self._cache.delete(cache_key)

            logger.info(f"系统配置已更新: {key} = {value}")
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"设置系统配置失败 {key}: {str(e)}")
            return False

    async def get_settings_by_category(
        self, db: AsyncSession, category: SettingCategory
    ) -> List[SystemSettings]:
        """
        根据分类获取配置列表

        Args:
            db: 数据库会话
            category: 配置分类

        Returns:
            配置列表
        """
        try:
            stmt = (
                select(SystemSettings)
                .where(SystemSettings.category == category)
                .order_by(SystemSettings.key)
            )

            result = await db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"获取分类配置失败 {category}: {str(e)}")
            return []

    async def get_all_settings(self, db: AsyncSession) -> List[SystemSettings]:
        """
        获取所有系统配置

        Args:
            db: 数据库会话

        Returns:
            所有配置列表
        """
        try:
            stmt = select(SystemSettings).order_by(
                SystemSettings.category, SystemSettings.key
            )

            result = await db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"获取所有配置失败: {str(e)}")
            return []

    def clear_cache(self, key: Optional[str] = None) -> None:
        """
        清除缓存

        Args:
            key: 特定配置键，如果为None则清除所有缓存
        """
        if key:
            cache_key = self._get_cache_key(key)
            self._cache.delete(cache_key)
        else:
            self._cache.clear()

    async def get_free_user_limits(self, db: AsyncSession) -> Dict[str, int]:
        """
        获取免费用户所有限制配置

        Returns:
            包含所有免费用户限制的字典
        """
        return {
            "background_generation_limit": await self.get_setting(
                db, "free_user_background_generation_limit", 3
            ),
            "chat_total_limit": await self.get_setting(
                db, "free_user_chat_total_limit", 100
            ),
            "chat_24h_limit": await self.get_setting(
                db,
                "free_user_chat_24h_limit",
                global_config_loaded_from_config_yaml.app.limits.free_user_chat_24h_limit,
            ),
            "guest_chat_24h_limit": await self.get_setting(
                db,
                "guest_user_chat_24h_limit",
                global_config_loaded_from_config_yaml.app.limits.guest_user_chat_24h_limit,
            ),
            "voice_24h_limit": await self.get_setting(
                db,
                "free_user_voice_24h_limit",
                global_config_loaded_from_config_yaml.app.limits.free_user_voice_24h_limit,
            ),
            "guest_voice_24h_limit": await self.get_setting(
                db,
                "guest_user_voice_24h_limit",
                global_config_loaded_from_config_yaml.app.limits.guest_user_voice_24h_limit,
            ),
            "image_gen_24h_limit": await self.get_setting(
                db,
                "free_user_image_gen_24h_limit",
                global_config_loaded_from_config_yaml.app.limits.free_user_image_gen_24h_limit,
            ),
            "agent_creation_24h_limit": await self.get_setting(
                db,
                "free_user_agent_creation_24h_limit",
                global_config_loaded_from_config_yaml.app.limits.free_user_agent_creation_24h_limit,
            ),
            "agent_creation_limit": await self.get_setting(
                db, "free_user_agent_creation_limit", 6
            ),
        }


# 创建全局实例
system_settings_service = SystemSettingsService()
