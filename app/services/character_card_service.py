import base64
import json
import os
import tempfile
from io import BytesIO
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, UploadFile
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.schemas.character_card import (
    CharacterCardImportRequest,
    CharacterCardImportResponse,
    CharacterCardV2,
    CharacterCardValidationError,
    CharacterCardValidationResponse,
)
from app.services import agent_service
from app.services.character_card_mapper import CharacterCardMapper


class CharacterCardService:
    """角色卡服务"""

    def __init__(self):
        self.mapper = CharacterCardMapper()

    async def import_character_card(
        self, request: CharacterCardImportRequest, user_id: str, db: AsyncSession
    ) -> CharacterCardImportResponse:
        """
        导入角色卡

        Args:
            request: 导入请求
            user_id: 用户ID
            db: 数据库会话

        Returns:
            导入响应
        """
        try:
            # 验证角色卡数据
            if isinstance(request.card_data, dict):
                card_data = CharacterCardV2(**request.card_data)
            else:
                card_data = request.card_data

            # 验证角色卡格式
            validation_result = await self.validate_character_card(card_data.dict())
            if not validation_result.is_valid:
                return CharacterCardImportResponse(
                    success=False,
                    message="角色卡验证失败",
                    warnings=[error.message for error in validation_result.errors],
                )

            # 检查是否存在同名角色
            if not request.override_existing:
                existing_agent = await self._check_existing_agent(
                    card_data.data.name, user_id, db
                )
                if existing_agent:
                    return CharacterCardImportResponse(
                        success=False,
                        message=f"已存在同名角色: {card_data.data.name}，请启用覆盖模式或更改角色名称",
                    )

            # 映射角色卡到Agent数据
            agent_data = self.mapper.map_card_to_agent(card_data, user_id)

            # 处理可选功能
            imported_features = [
                "basic_info",
                "personality",
                "scenario",
                "system_prompt",
            ]
            warnings = []

            if not request.import_character_book and agent_data.get("character_book"):
                agent_data["character_book"] = None
                warnings.append("角色书未导入")
            else:
                imported_features.append("character_book")

            if not request.import_alternate_greetings and agent_data.get(
                "alternate_greetings"
            ):
                agent_data["alternate_greetings"] = []
                warnings.append("替代问候语未导入")
            else:
                imported_features.append("alternate_greetings")

            # 处理 llm_config 字段
            if "llm_config" in agent_data:
                # 将 llm_config 移动到 settings 中
                if "settings" not in agent_data:
                    agent_data["settings"] = {}
                agent_data["settings"]["llm_config"] = agent_data.pop("llm_config")

            # 创建Agent
            agent = Agent(**agent_data)

            # 如果是覆盖模式，先删除现有Agent
            if request.override_existing:
                await self._delete_existing_agent(card_data.data.name, user_id, db)

            # 保存到数据库
            db.add(agent)
            await db.commit()
            await db.refresh(agent)

            logger.info(
                f"成功导入角色卡: {card_data.data.name} -> Agent ID: {agent.id}"
            )

            return CharacterCardImportResponse(
                success=True,
                message=f"成功导入角色卡: {card_data.data.name}",
                agent_id=agent.id,
                imported_features=imported_features,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"导入角色卡失败: {str(e)}")
            await db.rollback()
            return CharacterCardImportResponse(
                success=False, message=f"导入失败: {str(e)}"
            )

    async def import_character_card_from_file(
        self,
        file: UploadFile,
        user_id: str,
        db: AsyncSession,
        override_existing: bool = False,
        import_character_book: bool = True,
        import_alternate_greetings: bool = True,
    ) -> CharacterCardImportResponse:
        """
        从文件导入角色卡

        Args:
            file: 上传的文件
            user_id: 用户ID
            db: 数据库会话
            override_existing: 是否覆盖现有
            import_character_book: 是否导入角色书
            import_alternate_greetings: 是否导入替代问候语

        Returns:
            导入响应
        """
        try:
            # 读取文件内容
            file_content = await file.read()

            # 尝试解析角色卡数据
            card_data = None

            if file.filename.lower().endswith(".json"):
                # JSON文件
                card_data = await self._parse_json_file(file_content)
            elif file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                # 图片文件（角色卡可能嵌入在PNG metadata中）
                card_data = await self._parse_image_file(file_content)
            else:
                return CharacterCardImportResponse(
                    success=False, message="不支持的文件格式，请上传JSON或PNG文件"
                )

            if not card_data:
                return CharacterCardImportResponse(
                    success=False, message="无法从文件中解析角色卡数据"
                )

            # 创建导入请求
            request = CharacterCardImportRequest(
                card_data=card_data,
                override_existing=override_existing,
                import_character_book=import_character_book,
                import_alternate_greetings=import_alternate_greetings,
            )

            # 导入角色卡
            return await self.import_character_card(request, user_id, db)

        except Exception as e:
            logger.error(f"从文件导入角色卡失败: {str(e)}")
            return CharacterCardImportResponse(
                success=False, message=f"文件导入失败: {str(e)}"
            )

    async def export_agent_to_character_card(
        self,
        agent_id: str,
        user_id: str,
        db: AsyncSession,
        include_character_book: bool = True,
        include_alternate_greetings: bool = True,
        include_extensions: bool = True,
    ) -> CharacterCardV2:
        """
        将Agent导出为角色卡

        Args:
            agent_id: Agent ID
            user_id: 用户ID
            db: 数据库会话
            include_character_book: 是否包含角色书
            include_alternate_greetings: 是否包含替代问候语
            include_extensions: 是否包含扩展数据

        Returns:
            角色卡数据
        """
        # 获取Agent
        agent = await agent_service.get_agent_by_id(agent_id, user_id, db)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 构建Agent数据字典
        agent_data = {
            "id": agent.id,
            "name": agent.name,
            "intro": agent.intro,
            "opening": agent.opening,
            "main_prompt": agent.main_prompt,
            "mode_prompt": agent.mode_prompt,
            "personality": agent.personality,
            "scenario": agent.scenario,
            "message_example": agent.message_example,
            "creator_notes": agent.creator_notes,
            "post_history_instructions": agent.post_history_instructions,
            "alternate_greetings": (
                agent.alternate_greetings if include_alternate_greetings else []
            ),
            "character_book": agent.character_book if include_character_book else None,
            "tags": agent.tags,
            "character_version": agent.character_version,
            "extensions": agent.extensions if include_extensions else {},
            "character_card_data": agent.character_card_data,
            "creator": {"nickname": agent.creator.nickname if agent.creator else ""},
        }

        # 映射到角色卡
        return self.mapper.map_agent_to_card(agent_data)

    async def validate_character_card(
        self, card_data: Dict[str, Any]
    ) -> CharacterCardValidationResponse:
        """
        验证角色卡数据

        Args:
            card_data: 角色卡数据

        Returns:
            验证结果
        """
        errors = []
        warnings = []

        try:
            # 使用mapper验证
            validation_errors = self.mapper.validate_character_card(card_data)
            errors.extend(
                [
                    CharacterCardValidationError(
                        field="general", message=error, code="VALIDATION_ERROR"
                    )
                    for error in validation_errors
                ]
            )

            # 使用Pydantic验证
            try:
                CharacterCardV2(**card_data)
            except Exception as e:
                errors.append(
                    CharacterCardValidationError(
                        field="schema",
                        message=f"数据格式验证失败: {str(e)}",
                        code="SCHEMA_ERROR",
                    )
                )

            # 检查警告项
            data = card_data.get("data", {})
            if not data.get("personality"):
                warnings.append("建议添加角色性格描述")

            if not data.get("scenario"):
                warnings.append("建议添加场景设定")

            if not data.get("mes_example"):
                warnings.append("建议添加对话示例")

        except Exception as e:
            errors.append(
                CharacterCardValidationError(
                    field="general",
                    message=f"验证过程出错: {str(e)}",
                    code="VALIDATION_ERROR",
                )
            )

        return CharacterCardValidationResponse(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            supported_features=self.mapper.get_supported_features(),
        )

    async def _parse_json_file(self, file_content: bytes) -> Optional[Dict[str, Any]]:
        """
        解析JSON文件

        Args:
            file_content: 文件内容

        Returns:
            解析后的数据
        """
        try:
            content = file_content.decode("utf-8")
            return json.loads(content)
        except Exception as e:
            logger.error(f"解析JSON文件失败: {str(e)}")
            return None

    async def _parse_image_file(self, file_content: bytes) -> Optional[Dict[str, Any]]:
        """
        解析图片文件中的角色卡数据

        Args:
            file_content: 图片文件内容

        Returns:
            解析后的角色卡数据
        """
        try:
            # 尝试导入PIL
            try:
                from PIL import Image
            except ImportError:
                logger.warning("PIL未安装，无法解析图片文件中的角色卡数据")
                return None

            # 尝试从PNG的tEXt chunk中提取数据
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                tmp_file.write(file_content)
                tmp_file.flush()

                try:
                    with Image.open(tmp_file.name) as img:
                        # 检查PNG text数据
                        if hasattr(img, "text"):
                            for key, value in img.text.items():
                                if key.lower() in ["chara", "character", "card"]:
                                    try:
                                        # 尝试base64解码
                                        decoded = base64.b64decode(value)
                                        return json.loads(decoded.decode("utf-8"))
                                    except:
                                        try:
                                            # 直接解析JSON
                                            return json.loads(value)
                                        except:
                                            continue
                finally:
                    os.unlink(tmp_file.name)

            return None
        except Exception as e:
            logger.error(f"解析图片文件失败: {str(e)}")
            return None

    async def _check_existing_agent(
        self, name: str, user_id: str, db: AsyncSession
    ) -> Optional[Agent]:
        """
        检查是否存在同名Agent

        Args:
            name: 角色名称
            user_id: 用户ID
            db: 数据库会话

        Returns:
            存在的Agent或None
        """
        result = await db.execute(
            select(Agent).where(
                Agent.name == name,
                Agent.creator_id == user_id,
                Agent.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _delete_existing_agent(
        self, name: str, user_id: str, db: AsyncSession
    ) -> None:
        """
        删除现有的同名Agent

        Args:
            name: 角色名称
            user_id: 用户ID
            db: 数据库会话
        """
        existing_agent = await self._check_existing_agent(name, user_id, db)
        if existing_agent:
            await agent_service.delete_agent(existing_agent.id, user_id, db)
            logger.info(f"删除现有Agent: {existing_agent.id}")


# 创建服务实例
character_card_service = CharacterCardService()
