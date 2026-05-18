"""评测会话管理服务"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent
from app.models.evaluation import (
    EvaluationInteraction,
    EvaluationResult,
    EvaluationSession,
    EvaluationStatus,
)
from app.services import agent_service, chat_service
from app.services.scoring_service import ScoringService

from loguru import logger


class EvaluationService:
    """评测服务 - 负责管理评测会话的生命周期"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scoring_service = ScoringService()
        self._active_sessions: Dict[str, Dict] = {}  # 内存中的活跃会话状态

    async def create_session(
        self,
        creator_id: str,
        name: str,
        questions: List[str],
        selected_agents: List[str],
        scoring_model: str,
        scoring_criteria: Optional[str] = None,
        use_new_user_identity: bool = False,
        config: Optional[Dict[str, Any]] = None,
    ) -> EvaluationSession:
        """创建评测会话"""

        # 验证智能体是否存在
        stmt = select(Agent).where(Agent.id.in_(selected_agents))
        result = await self.db.execute(stmt)
        agents = result.scalars().all()

        if len(agents) != len(selected_agents):
            missing_agents = set(selected_agents) - {
                agent.id for agent in agents
            }
            raise ValueError(f"Agents not found: {missing_agents}")

        # 创建会话
        session = EvaluationSession(
            id=str(uuid.uuid4()),
            name=name,
            creator_id=creator_id,
            questions=questions,
            selected_agents=selected_agents,
            scoring_model=scoring_model,
            scoring_criteria=scoring_criteria,
            use_new_user_identity=use_new_user_identity,
            config=config or {},
            total_tests=len(questions) * len(selected_agents),
            completed_tests=0,
        )

        try:
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建评测会话失败: {str(e)}")
            raise

        logger.info(
            f"创建评测会话: {session.id}, 问题数: {len(questions)}, 智能体数: {len(selected_agents)}"
        )
        return session

    async def start_session(self, session_id: str) -> bool:
        """启动评测会话"""

        # 获取会话信息
        stmt = select(EvaluationSession).where(
            EvaluationSession.id == session_id
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise ValueError(f"Evaluation session not found: {session_id}")

        if session.status != EvaluationStatus.PENDING:
            raise ValueError(
                f"Invalid evaluation session status: {session.status}"
            )

        # 更新会话状态
        await self.db.execute(
            update(EvaluationSession)
            .where(EvaluationSession.id == session_id)
            .values(
                status=EvaluationStatus.RUNNING, started_at=datetime.utcnow()
            )
        )
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"数据库操作失败: {str(e)}")
            raise

        # 初始化会话状态
        self._active_sessions[session_id] = {
            "status": "running",
            "progress": 0,
            "current_test": 0,
            "results": [],
            "websocket_connections": [],
        }

        # 异步启动测试任务，传递会话ID而不是会话对象
        asyncio.create_task(self._execute_session(session.id))

        logger.info(f"启动评测会话: {session_id}")
        return True

    async def _execute_session(self, session_id: str):
        """执行评测会话 - 异步任务"""
        # 创建新的数据库会话用于后台任务
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as db_session:
            # 创建新的EvaluationService实例用于后台任务
            bg_service = EvaluationService(db_session)
            # 共享内存状态
            bg_service._active_sessions = self._active_sessions

            try:
                # 重新获取会话对象
                stmt = select(EvaluationSession).where(
                    EvaluationSession.id == session_id
                )
                result = await db_session.execute(stmt)
                session = result.scalar_one_or_none()

                if not session:
                    logger.error(f"评测会话不存在: {session_id}")
                    return

                session_state = self._active_sessions.get(session_id)
                if not session_state:
                    logger.error(f"内存中的会话状态不存在: {session_id}")
                    return

                # 广播开始消息
                await bg_service._broadcast_update(
                    session.id,
                    {
                        "type": "session_started",
                        "session_id": session.id,
                        "total_tests": session.total_tests,
                    },
                )

                # 执行每个测试 - 并行优化
                test_index = 0

                # 为每个问题创建并行任务
                for question_index, question in enumerate(session.questions):
                    # 创建当前问题的所有智能体测试任务
                    agent_tasks = []
                    question_test_indices = []

                    for agent_id in session.selected_agents:
                        test_index += 1
                        question_test_indices.append(test_index)

                        # 广播进度更新
                        await bg_service._broadcast_update(
                            session.id,
                            {
                                "type": "test_started",
                                "session_id": session.id,
                                "test_index": test_index,
                                "question_index": question_index,
                                "question": question,
                                "agent_id": agent_id,
                                "progress": int(
                                    (test_index / session.total_tests) * 100
                                ),
                            },
                        )

                        # 创建异步任务 - 传递会话ID而不是会话对象，避免数据库连接冲突
                        task = bg_service._execute_single_test_with_new_session(
                            session.id, question, question_index, agent_id
                        )
                        agent_tasks.append(task)

                    # 并行执行当前问题的所有智能体测试
                    logger.debug(
                        f"并行执行问题 {question_index + 1} 的 {len(agent_tasks)} 个智能体测试"
                    )
                    results = await asyncio.gather(
                        *agent_tasks, return_exceptions=True
                    )

                    # 处理并行执行的结果
                    for i, result in enumerate(results):
                        current_test_index = question_test_indices[i]

                        if isinstance(result, Exception):
                            logger.error(
                                f"测试执行异常 {current_test_index}: {str(result)}"
                            )
                            continue

                        if result:
                            session_state["results"].append(result)
                            session_state["current_test"] = current_test_index
                            session_state["progress"] = int(
                                (current_test_index / session.total_tests) * 100
                            )

                            # 广播测试完成
                            await bg_service._broadcast_update(
                                session.id,
                                {
                                    "type": "test_completed",
                                    "session_id": session.id,
                                    "result": bg_service._serialize_result(
                                        result
                                    ),
                                },
                            )

                    logger.debug(
                        f"问题 {question_index + 1} 的并行测试完成，成功 {len([r for r in results if not isinstance(r, Exception) and r])} 个"
                    )

                # 完成会话
                await bg_service._complete_session(session.id)

            except Exception as e:
                logger.error(f"评测会话执行失败 {session.id}: {str(e)}")
                await bg_service._fail_session(session.id, str(e))

    async def _execute_single_test_with_new_session(
        self, session_id: str, question: str, question_index: int, agent_id: str
    ) -> Optional[EvaluationResult]:
        """为并行执行创建独立数据库会话的单个测试方法"""
        from app.db.session import AsyncSessionLocal

        # 为每个并行任务创建独立的数据库会话
        async with AsyncSessionLocal() as test_db_session:
            try:
                # 创建独立的EvaluationService实例
                test_service = EvaluationService(test_db_session)

                # 重新获取会话信息
                stmt = select(EvaluationSession).where(
                    EvaluationSession.id == session_id
                )
                result = await test_db_session.execute(stmt)
                session = result.scalar_one_or_none()

                if not session:
                    logger.error(f"评测会话不存在: {session_id}")
                    return None

                # 执行测试
                return await test_service._execute_single_test(
                    session, question, question_index, agent_id
                )

            except Exception as e:
                logger.error(f"独立会话测试执行失败 {session_id}: {str(e)}")
                return None

    async def _execute_single_test(
        self,
        session: EvaluationSession,
        question: str,
        question_index: int,
        agent_id: str,
    ) -> Optional[EvaluationResult]:
        """执行单个测试"""

        result = EvaluationResult(
            id=str(uuid.uuid4()),
            session_id=session.id,
            agent_id=agent_id,
            question=question,
            question_index=question_index,
            is_success=False,
        )

        try:
            # 获取智能体信息
            stmt = select(Agent).where(Agent.id == agent_id)
            db_result = await self.db.execute(stmt)
            agent = db_result.scalar_one_or_none()

            if not agent:
                result.error_message = f"Agent not found: {agent_id}"
                await self._save_result(result)
                return result

            # 准备用户身份
            user_identity = await self._prepare_user_identity(session)

            # 发起对话
            start_time = datetime.utcnow()
            chat_response = await self._send_evaluation_message(
                agent_id=agent_id,
                question=question,
                user_identity=user_identity,
            )
            end_time = datetime.utcnow()

            if not chat_response or not chat_response.get("response"):
                result.error_message = "Agent did not return a response"
                await self._save_result(result)
                return result

            agent_response = chat_response["response"]
            response_time = (end_time - start_time).total_seconds()

            # 记录交互
            interaction = EvaluationInteraction(
                id=str(uuid.uuid4()),
                session_id=session.id,
                result_id=result.id,
                chat_id=chat_response.get("chat_id"),
                user_input=question,
                agent_response=agent_response,
                interaction_order=1,
                user_identity=user_identity,
                response_metadata=chat_response.get("metadata", {}),
            )

            # 评分
            if session.scoring_criteria:
                scoring_result = await self.scoring_service.score_response(
                    question=question,
                    agent_response=agent_response,
                    agent_info={
                        "name": agent.name,
                        "intro": agent.intro,
                        "personality": agent.personality or agent.prompt,
                    },
                    scoring_model=session.scoring_model,
                    scoring_criteria=session.scoring_criteria,
                )

                if scoring_result["success"]:
                    result.overall_score = scoring_result.get("overall_score")
                    result.detailed_scores = scoring_result.get(
                        "detailed_scores"
                    )
                    result.scoring_reason = scoring_result.get("reason")
                    result.scoring_model_used = session.scoring_model

            # 更新结果
            result.agent_response = agent_response
            result.agent_name = agent.name  # 保存智能体名称
            result.response_time = response_time
            result.is_success = True

            # 保存到数据库
            await self._save_result(result)
            await self._save_interaction(interaction)

            return result

        except Exception as e:
            logger.error(f"测试执行失败 {session.id}: {str(e)}")
            result.error_message = str(e)
            await self._save_result(result)
            return result

    async def _prepare_user_identity(
        self, session: EvaluationSession
    ) -> Dict[str, Any]:
        """准备用户身份信息"""
        if session.use_new_user_identity:
            # 创建临时游客身份
            device_id = f"eval_{session.id}_{uuid.uuid4().hex[:8]}"
            return {
                "type": "guest",
                "device_id": device_id,
                "session_id": session.id,
            }
        else:
            # 使用创建者身份
            return {
                "type": "user",
                "user_id": session.creator_id,
                "session_id": session.id,
            }

    async def _send_evaluation_message(
        self, agent_id: str, question: str, user_identity: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """发送评测消息 - 完全使用现有聊天系统的chat_completions接口"""
        try:
            # 获取或创建聊天会话
            if user_identity["type"] == "guest":
                # 对于游客身份，创建临时用户ID
                temp_user_id = f"eval_user_{uuid.uuid4().hex[:8]}"
            else:
                temp_user_id = user_identity["user_id"]

            # 使用现有聊天服务获取或创建聊天
            chat = await chat_service.get_or_create_chat_by_agent(
                db=self.db, user_id=temp_user_id, agent_id=agent_id
            )

            # 直接使用现有的智能体管理器和完全相同的聊天逻辑
            # 这确保评测使用的是与正常聊天完全相同的代码路径
            from app.core.agent.agent import agent_manager

            agent_instance = await agent_manager.get_agent(agent_id)

            if not agent_instance:
                logger.error(f"智能体实例不存在: {agent_id}")
                return None

            # 构造OpenAI格式的消息 - 与现有聊天API完全一致
            messages = [{"role": "user", "content": question}]

            # 调用智能体的chat_completions方法 - 这与 /chats/agents/{agent_id}/chat/completions 使用完全相同的逻辑
            response = await agent_instance.chat_completions(
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
                stream=False,
                # 传递聊天会话信息，确保记忆系统正常工作
                session_id=chat.id if chat else None,
            )

            if not response or not response.get("choices"):
                logger.error(f"智能体未返回有效响应: {agent_id}")
                return None

            agent_response = response["choices"][0]["message"]["content"]

            # 返回与现有聊天API一致的格式
            return {
                "response": agent_response,
                "chat_id": chat.id if chat else None,
                "metadata": {
                    "model": response.get("model"),
                    "usage": response.get("usage"),
                    "created": response.get("created"),
                    "id": response.get("id"),
                    "object": response.get("object"),
                },
            }

        except Exception as e:
            logger.error(f"发送评测消息失败 {agent_id}: {str(e)}")
            logger.exception("详细错误信息:")
            return None

    async def _save_result(self, result: EvaluationResult):
        """保存测试结果"""
        try:
            # 在一个事务中保存结果和更新统计
            self.db.add(result)

            # 更新会话统计
            await self.db.execute(
                update(EvaluationSession)
                .where(EvaluationSession.id == result.session_id)
                .values(completed_tests=EvaluationSession.completed_tests + 1)
            )

            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"保存评测结果失败: {str(e)}")
            raise

    async def _save_interaction(self, interaction: EvaluationInteraction):
        """保存交互记录"""
        self.db.add(interaction)
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"数据库操作失败: {str(e)}")
            raise

    async def _complete_session(self, session_id: str):
        """完成评测会话"""
        # 计算统计信息
        stats = await self._calculate_session_stats(session_id)

        # 更新会话状态
        await self.db.execute(
            update(EvaluationSession)
            .where(EvaluationSession.id == session_id)
            .values(
                status=EvaluationStatus.COMPLETED,
                completed_at=datetime.utcnow(),
                success_rate=stats["success_rate"],
                average_score=stats["average_score"],
            )
        )
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"数据库操作失败: {str(e)}")
            raise

        # 广播完成消息
        await self._broadcast_update(
            session_id,
            {
                "type": "session_completed",
                "session_id": session_id,
                "stats": stats,
            },
        )

        # 清理内存状态
        self._active_sessions.pop(session_id, None)

        logger.info(f"评测会话完成: {session_id}")

    async def _fail_session(self, session_id: str, error_message: str):
        """失败的评测会话"""
        await self.db.execute(
            update(EvaluationSession)
            .where(EvaluationSession.id == session_id)
            .values(
                status=EvaluationStatus.FAILED, completed_at=datetime.utcnow()
            )
        )
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"数据库操作失败: {str(e)}")
            raise

        await self._broadcast_update(
            session_id,
            {
                "type": "session_failed",
                "session_id": session_id,
                "error": error_message,
            },
        )

        self._active_sessions.pop(session_id, None)

        logger.error(f"评测会话失败: {session_id}, 错误: {error_message}")

    async def _calculate_session_stats(self, session_id: str) -> Dict[str, Any]:
        """计算会话统计信息"""
        stmt = select(EvaluationResult).where(
            EvaluationResult.session_id == session_id
        )
        result = await self.db.execute(stmt)
        results = result.scalars().all()

        if not results:
            return {"success_rate": 0.0, "average_score": None}

        successful_results = [r for r in results if r.is_success]
        success_rate = len(successful_results) / len(results)

        scores = [
            r.overall_score for r in results if r.overall_score is not None
        ]
        average_score = sum(scores) / len(scores) if scores else None

        return {
            "success_rate": success_rate,
            "average_score": average_score,
            "total_tests": len(results),
            "successful_tests": len(successful_results),
        }

    async def _broadcast_update(self, session_id: str, message: Dict[str, Any]):
        """广播更新到WebSocket连接"""
        session_state = self._active_sessions.get(session_id)
        if not session_state:
            return

        connections = session_state.get("websocket_connections", [])
        if not connections:
            return

        # 这里应该实现WebSocket广播逻辑
        # 暂时只记录日志
        logger.debug(f"广播消息到 {len(connections)} 个连接: {message['type']}")

    def _serialize_result(self, result: EvaluationResult) -> Dict[str, Any]:
        """序列化结果用于传输"""
        return {
            "id": result.id,
            "agent_id": result.agent_id,
            "agent_name": result.agent_name,
            "question": result.question,
            "question_index": result.question_index,
            "agent_response": result.agent_response,
            "response_time": result.response_time,
            "overall_score": result.overall_score,
            "detailed_scores": result.detailed_scores,
            "scoring_reason": result.scoring_reason,
            "is_success": result.is_success,
            "error_message": result.error_message,
            "created_at": (
                result.created_at.isoformat() if result.created_at else None
            ),
        }

    async def get_session(self, session_id: str) -> Optional[EvaluationSession]:
        """获取评测会话"""
        stmt = (
            select(EvaluationSession)
            .options(
                selectinload(EvaluationSession.results),
                selectinload(EvaluationSession.interactions),
                selectinload(EvaluationSession.creator),
            )
            .where(EvaluationSession.id == session_id)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_sessions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> List[EvaluationSession]:
        """获取用户的评测会话列表"""
        stmt = (
            select(EvaluationSession)
            .options(
                selectinload(EvaluationSession.results),
                selectinload(EvaluationSession.interactions),
                selectinload(EvaluationSession.creator),
            )
            .where(EvaluationSession.creator_id == user_id)
        )

        if status:
            try:
                status_enum = EvaluationStatus(status)
                stmt = stmt.where(EvaluationSession.status == status_enum)
            except ValueError:
                # 忽略无效的状态值
                pass

        stmt = (
            stmt.order_by(EvaluationSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_session_results(
        self, session_id: str
    ) -> List[EvaluationResult]:
        """获取会话结果"""
        stmt = (
            select(EvaluationResult)
            .where(EvaluationResult.session_id == session_id)
            .order_by(
                EvaluationResult.question_index, EvaluationResult.created_at
            )
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def cancel_session(self, session_id: str) -> bool:
        """取消评测会话"""
        session_state = self._active_sessions.get(session_id)
        if session_state:
            session_state["status"] = "cancelled"

        await self.db.execute(
            update(EvaluationSession)
            .where(EvaluationSession.id == session_id)
            .values(
                status=EvaluationStatus.CANCELLED,
                completed_at=datetime.utcnow(),
            )
        )
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"数据库操作失败: {str(e)}")
            raise

        await self._broadcast_update(
            session_id, {"type": "session_cancelled", "session_id": session_id}
        )

        self._active_sessions.pop(session_id, None)

        logger.info(f"取消评测会话: {session_id}")
        return True

    def add_websocket_connection(self, session_id: str, websocket):
        """添加WebSocket连接"""
        session_state = self._active_sessions.get(session_id)
        if session_state:
            session_state["websocket_connections"].append(websocket)

    def remove_websocket_connection(self, session_id: str, websocket):
        """移除WebSocket连接"""
        session_state = self._active_sessions.get(session_id)
        if session_state and "websocket_connections" in session_state:
            connections = session_state["websocket_connections"]
            if websocket in connections:
                connections.remove(websocket)

    async def _send_evaluation_message(
        self, agent_id: str, question: str, user_identity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """发送评测消息给智能体

        Args:
            agent_id: 智能体ID
            question: 测试问题
            user_identity: 用户身份信息

        Returns:
            包含回复内容和元数据的字典
        """
        try:
            from langchain_core.messages import HumanMessage

            # 获取智能体数据（用于创建Agent实例）
            agent_data = await agent_service.get_agent_for_chat(
                self.db, agent_id=agent_id
            )
            if not agent_data:
                raise ValueError(f"Failed to fetch agent data: {agent_id}")

            # 从AgentManager获取Agent实例
            from app.core.agent.agent import agent_manager

            agent = await agent_manager.get_agent(agent_data)

            # 构建消息格式
            messages = [HumanMessage(content=question)]

            # 为评测创建临时会话ID - 使用完整UUID格式
            eval_session_id = str(uuid.uuid4())

            # 确定用户ID
            if user_identity["type"] == "user":
                user_id = user_identity["user_id"]
            else:
                # 对于游客身份，使用设备ID作为用户标识
                user_id = f"guest_{user_identity['device_id']}"

            # 调用智能体进行对话
            response_content = await agent.chat(
                user_id=user_id,
                session_id=eval_session_id,
                messages=messages,
            )

            # 如果需要，可以获取或创建聊天会话记录
            chat = None
            if user_identity["type"] == "user":
                try:
                    chat = await chat_service.get_or_create_chat_by_agent(
                        db=self.db,
                        user_id=user_identity["user_id"],
                        agent_id=agent_id,
                    )
                except Exception as e:
                    logger.warning(
                        f"创建聊天会话失败，但评测可以继续: {str(e)}"
                    )

            return {
                "response": response_content,
                "chat_id": chat.id if chat else None,
                "session_id": eval_session_id,
                "agent_name": agent_data.get("name"),
                "metadata": {
                    "user_identity": user_identity,
                    "agent_id": agent_id,
                    "question_length": len(question),
                    "response_length": (
                        len(response_content) if response_content else 0
                    ),
                },
            }

        except Exception as e:
            logger.error(
                f"评测消息发送失败 - Agent: {agent_id}, 错误: {str(e)}"
            )
            raise ValueError(f"Agent communication failed: {str(e)}")
