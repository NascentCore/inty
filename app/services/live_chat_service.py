"""
实时语音通话服务
使用 Gemini Live API 实现 Agent 实时语音对话

CREATED_BY_AGENT
"""

import asyncio
import base64
import os
import re
import tempfile
import time
import uuid
from collections import deque
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

from google import genai
from google.genai import types
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent.agent import agent_manager
from app.core.agentic_kernel.providers.gemini import (
    GeminiClientOptions,
    get_gemini_client as get_kernel_gemini_client,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.core.voice import tts_api as voice_tts_api
from app.schemas.live_chat import LiveChatConfig, LiveChatStatus
from app.services import agent_service, chat_history_service
from app.services.chat_service import (
    generate_session_id,
    get_or_create_chat_by_agent,
    get_or_create_chat_settings,
)
from app.services.gcs_service import GCSService
from app.utils.audio import build_interleaved_pcm_24k

# 语音通话默认音色映射（按性别选择 Gemini 预置音色）
GENDER_TO_GEMINI_VOICE_MAPPING = {
    "MALE": "Puck",
    "FEMALE": "Zephyr",
    "OTHER": "Kore",
}


@dataclass
class LiveSession:
    """实时语音通话会话状态"""

    session_id: str
    agent_id: str
    user_id: str
    chat_id: str
    voice_session_id: str = ""
    status: LiveChatStatus = LiveChatStatus.CONNECTING
    config: LiveChatConfig = field(default_factory=LiveChatConfig)
    gemini_session: Any = None
    gemini_cm: Any = None
    receive_task: Optional[asyncio.Task] = None
    session_handle: Optional[str] = None
    user_transcript_buffer: str = ""
    ai_transcript_buffer: str = ""
    gemini_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    reconnect_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    reconnect_count: int = 0
    # 预填充完成事件：receive_loop 收到首个 turn_complete（无 model_turn）时 set，
    # 在此之前音频发送到 Gemini 可能被丢弃（模型还在处理预填充）。
    prefill_complete: asyncio.Event = field(
        default_factory=asyncio.Event, repr=False
    )
    pending_audio: deque[bytes] = field(
        default_factory=lambda: deque(maxlen=1000), repr=False
    )
    pending_user_transcript: str = ""
    pending_ai_transcript: str = ""
    user_transcription_updates: int = 0
    ai_transcription_updates: int = 0
    last_user_transcription_piece: str = ""
    last_ai_transcription_piece: str = ""
    # Token 用量统计（由 Gemini Live API 周期性返回）
    total_token_count: int = 0
    response_token_details: Dict[str, int] = field(default_factory=dict)
    # 延迟追踪字段
    connect_start_time: Optional[float] = None
    connect_end_time: Optional[float] = None
    last_audio_sent_time: Optional[float] = None
    turn_latencies: List[float] = field(default_factory=list)
    current_turn_start_time: Optional[float] = None
    last_response_after_silence_ms: Optional[int] = None
    # 按对话顺序累积的音频（"user" | "ai", bytes），用于保存单路 WAV 到 GCS
    conversation_audio_chunks: List[Tuple[str, bytes]] = field(
        default_factory=list, repr=False
    )

    def get_latency_metrics(self) -> dict:
        """计算并返回延迟指标"""
        metrics: Dict[str, Any] = {}
        if self.connect_start_time and self.connect_end_time:
            metrics["connect_latency_ms"] = int(
                (self.connect_end_time - self.connect_start_time) * 1000
            )
        if self.last_response_after_silence_ms is not None:
            metrics["first_response_after_silence_ms"] = (
                self.last_response_after_silence_ms
            )
        if self.turn_latencies:
            metrics["turn_latencies_ms"] = [int(t * 1000) for t in self.turn_latencies]
            metrics["avg_turn_latency_ms"] = int(
                sum(self.turn_latencies) / len(self.turn_latencies) * 1000
            )
        return metrics


class LiveChatService:
    """实时语音通话服务"""

    def __init__(self):
        self._config = global_config_loaded_from_config_yaml.gemini_live
        self._client: Optional[genai.Client] = None
        self._active_sessions: Dict[str, LiveSession] = {}

    def _get_client(self) -> genai.Client:
        """获取或创建 Gemini 客户端"""
        if self._client is None:
            gcp_key_path = (
                global_config_loaded_from_config_yaml.app.gcp_service_account_key
            )
            self._client = get_kernel_gemini_client(
                GeminiClientOptions(
                    vertexai=True,
                    project=self._config.project_id,
                    location=self._config.location,
                    wrap_langsmith=True,
                    tags=("google-genai", "gemini-live", "app-services-live-chat"),
                    metadata={
                        "source": "app.services.live_chat_service",
                        "project_id": self._config.project_id,
                        "location": self._config.location,
                    },
                    chat_name="Inty_GeminiLive",
                    credentials_path=gcp_key_path,
                )
            )
            if gcp_key_path and os.path.exists(gcp_key_path):
                logger.debug(f"设置 GCP 凭证: {gcp_key_path}")
            logger.info(
                f"Gemini Live 客户端已初始化 - project: {self._config.project_id}, "
                f"location: {self._config.location}"
            )
        return self._client

    async def create_session(
        self,
        db: AsyncSession,
        agent_id: str,
        user_id: str,
        config: Optional[LiveChatConfig] = None,
    ) -> LiveSession:
        """
        创建实时语音通话会话

        复用现有的 chat 系统：
        1. 获取或创建 chat 会话
        2. 获取 Agent 定义和对话历史
        3. 构建 system instruction
        """
        if not self._config.enabled:
            raise ValueError("Live voice chat is not enabled")

        chat = await get_or_create_chat_by_agent(db, user_id, agent_id)
        session_id = generate_session_id(chat.id)

        agent_data = await agent_service.get_agent_for_chat(db, agent_id=agent_id)
        if not agent_data:
            raise ValueError(f"Agent not found: {agent_id}")

        agent = await agent_manager.get_agent(agent_data)

        session = LiveSession(
            session_id=session_id,
            agent_id=agent_id,
            user_id=user_id,
            chat_id=chat.id,
            voice_session_id=str(uuid.uuid4()),
            config=config or LiveChatConfig(),
        )

        self._active_sessions[session_id] = session
        logger.info(
            f"创建 Live 会话 - session_id: {session_id}, agent_id: {agent_id}, "
            f"user_id: {user_id}"
        )

        return session

    def _build_system_instruction(
        self,
        agent_data: dict,
        history_messages: List[Any],
        merged_response_language_name: Optional[str] = None,
    ) -> str:
        """
        构建 Gemini Live 的 system instruction

        包含：
        1. Agent 的 personality/scenario/intro
        2. 对话历史摘要（如果有）
        """
        parts = []

        if agent_data.get("personality"):
            parts.append(f"## 角色人设\n{agent_data['personality']}")

        if agent_data.get("scenario"):
            parts.append(f"## 场景设定\n{agent_data['scenario']}")

        if agent_data.get("intro"):
            parts.append(f"## 角色介绍\n{agent_data['intro']}")

        if agent_data.get("message_example"):
            parts.append(f"## 对话示例\n{agent_data['message_example']}")

        if history_messages:
            history_summary = self._summarize_history(history_messages)
            if history_summary:
                parts.append(f"## 之前的对话\n{history_summary}")

        parts.append(
            self._build_live_response_constraints(
                merged_response_language_name=merged_response_language_name
            )
        )

        return "\n\n".join(parts)

    def _build_live_response_constraints(
        self, merged_response_language_name: Optional[str] = None
    ) -> str:
        """构建 Live 对话回复约束。

        对于 native-audio 模型（gemini-live-2.5-flash-native-audio），
        speech_config.language_code 不生效，必须通过 system instruction 强制约束语言。
        参考: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api/configure-language-voice
        """
        parts = [
            "## 输出格式\n"
            "这是实时语音对话，请直接用自然口语回复，不要使用括号描述动作或场景。"
        ]

        if merged_response_language_name is None:
            response_language_name = (
                getattr(self._config, "response_language_name", "") or ""
            ).strip()
        else:
            response_language_name = (merged_response_language_name or "").strip()
        if response_language_name:
            parts.append(
                "## CRITICAL LANGUAGE RULE - YOU MUST FOLLOW THIS EXACTLY\n\n"
                f"YOU MUST SPEAK ONLY IN {response_language_name} AT ALL TIMES. "
                "This is a strict requirement that cannot be overridden. "
                "Even if the user speaks to you in a different language, "
                "you MUST reply ONLY in the required language. "
                "DO NOT code-switch or mix languages under any circumstances. "
                "DO NOT translate what the user said — just respond naturally in the required language. "
                "If you are unsure, default to the required language. "
                "VIOLATING THIS RULE IS UNACCEPTABLE."
            )
        return "\n\n".join(parts)

    @staticmethod
    def _message_content_to_text(content: Any) -> str:
        """
        将消息内容转换为纯文本，兼容字符串和 OpenAI content parts。
        """
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts: List[str] = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        text_parts.append(text.strip())
            return "\n".join(text_parts)
        return ""

    def _build_system_instruction_from_text_chat_system_messages(
        self,
        system_messages: List[SystemMessage],
        merged_response_language_name: Optional[str] = None,
    ) -> str:
        """
        用文本聊天系统消息构建 Live system instruction，保持与文本聊天一致。
        """
        instruction_parts: List[str] = []
        for message in system_messages:
            text = self._message_content_to_text(getattr(message, "content", ""))
            if text:
                instruction_parts.append(text)
        instruction_parts.append(
            self._build_live_response_constraints(
                merged_response_language_name=merged_response_language_name
            )
        )
        return "\n\n".join(instruction_parts)

    def _build_prefill_turns_from_history_messages(
        self, history_messages: List[BaseMessage]
    ) -> List[types.Content]:
        """
        将文本聊天历史（用户/AI）转换为 Gemini Live 预填充 turns。
        """
        turns: List[types.Content] = []
        for message in history_messages:
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "model"
            else:
                continue

            text = self._message_content_to_text(getattr(message, "content", ""))
            if not text:
                continue
            turns.append(types.Content(role=role, parts=[types.Part(text=text)]))
        return turns

    def _summarize_history(self, messages: List[Any], max_turns: int = 10) -> str:
        """将对话历史转换为文本摘要"""
        if not messages:
            return ""

        recent_messages = messages[-max_turns * 2 :]
        lines = []

        for msg in recent_messages:
            if isinstance(msg, HumanMessage):
                lines.append(f"用户: {msg.content}")
            elif isinstance(msg, AIMessage):
                clean_content = self._strip_roleplay_markup(msg.content)
                if clean_content:
                    lines.append(f"AI: {clean_content}")

        return "\n".join(lines)

    def _strip_roleplay_markup(self, content: str) -> str:
        """移除角色扮演格式标记，只保留纯对话文本"""
        text = re.sub(r"\([^)]*\)", "", content)
        text = text.replace('"', "").replace(""", "").replace(""", "")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    _CJK_RE = re.compile(r"[\u4e00-\u9fff]")
    _CJK_SPACE_RE = re.compile(r"([\u4e00-\u9fff])\s+([\u4e00-\u9fff])")
    _DIGIT_SPACE_RE = re.compile(r"(\d)\s+(?=\d)")

    def _merge_transcription_piece(self, current: str, new_piece: str) -> str:
        if not new_piece:
            return current
        if not current:
            return new_piece
        if new_piece.startswith(current):
            return new_piece
        if current.startswith(new_piece):
            return current
        if current.endswith(new_piece):
            return current
        if new_piece.endswith(current):
            return new_piece
        # 追加：尽量保持原始分片里的空格/标点
        if (
            current
            and new_piece
            and not current.endswith((" ", "\n"))
            and not new_piece.startswith(
                (
                    " ",
                    "\n",
                    ",",
                    ".",
                    "!",
                    "?",
                    "，",
                    "。",
                    "！",
                    "？",
                    "、",
                    "：",
                    "；",
                    ")",
                    "”",
                    '"',
                    "'",
                )
            )
        ):
            return current + " " + new_piece
        return current + new_piece

    def _normalize_transcript_text(self, text: str) -> str:
        t = (text or "").strip()
        if not t:
            return ""
        # 若包含中文，去掉中文字符间的空格；同时把数字间空格合并（例如 "1 2 3"->"123"）
        if self._CJK_RE.search(t):
            while True:
                new_t = self._CJK_SPACE_RE.sub(r"\1\2", t)
                if new_t == t:
                    break
                t = new_t
            t = self._DIGIT_SPACE_RE.sub(r"\1", t)
        # 压缩多余空白
        t = " ".join(t.split())
        return t

    # Gemini Live API 支持的预设语音名称
    # Gemini Live API 支持的预设语音（Chirp 3: HD voices）
    # 来源: https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd
    GEMINI_PREBUILT_VOICES = {
        "Zephyr",
        "Puck",
        "Charon",
        "Kore",
        "Fenrir",
        "Aoede",
        "Orus",
        "Leda",
        "Achernar",
        "Achird",
        "Algenib",
        "Algieba",
        "Alnilam",
        "Autonoe",
        "Callirrhoe",
        "Despina",
        "Enceladus",
        "Erinome",
        "Gacrux",
        "Iapetus",
        "Laomedeia",
        "Pulcherrima",
        "Rasalgethi",
        "Sadachbia",
        "Sadaltager",
        "Schedar",
        "Sulafat",
        "Umbriel",
        "Vindemiatrix",
        "Zubenelgenubi",
    }

    def _resolved_speech_language_code(self, session: LiveSession) -> str:
        ov = session.config.speech_language_code
        if ov is not None and ov.strip():
            return ov.strip()
        return (getattr(self._config, "speech_language_code", "") or "").strip()

    def _resolved_response_language_name(self, session: LiveSession) -> str:
        ov = session.config.response_language_name
        if ov is not None and ov.strip():
            return ov.strip()
        speech_ov = session.config.speech_language_code
        if speech_ov is not None and speech_ov.strip():
            return speech_ov.strip()
        return (getattr(self._config, "response_language_name", "") or "").strip()

    def _build_live_config(
        self,
        *,
        merged_speech_language_code: str,
        voice_id: Optional[str] = None,
        agent_gender: Optional[str] = None,
        system_instruction: Optional[str] = None,
        session_handle: Optional[str] = None,
    ) -> types.LiveConnectConfig:
        """构建 Gemini Live 连接配置。

        Args:
            session_handle: 会话恢复句柄。传入时使用 SessionResumptionConfig
                           恢复之前的对话上下文，而非创建全新会话。
        """
        fallback_voice_name = GENDER_TO_GEMINI_VOICE_MAPPING.get(
            agent_gender, self._config.default_voice
        )
        prefix, raw = voice_tts_api.parse_voice_id(voice_id or "")
        if (
            voice_id
            and prefix == voice_tts_api.VOICE_ID_PREFIX_GEMINI
            and raw in self.GEMINI_PREBUILT_VOICES
        ):
            voice_name = raw
        elif voice_id and prefix == "" and voice_id in self.GEMINI_PREBUILT_VOICES:
            voice_name = voice_id
        else:
            voice_name = fallback_voice_name
            if voice_id and prefix == voice_tts_api.VOICE_ID_PREFIX_GEMINI:
                logger.warning(
                    f"Unknown Gemini voice_id: {voice_id}, fallback to {voice_name}"
                )
            elif voice_id:
                logger.debug(
                    f"voice_id '{voice_id}' 不是 Gemini 预设语音（prefix={prefix or 'none'}），"
                    f"根据性别 {agent_gender} 使用默认语音: {voice_name}"
                )

        speech_config_kwargs: Dict[str, Any] = {
            "voice_config": types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        }
        speech_language_code = (merged_speech_language_code or "").strip()
        speech_fields = getattr(types.SpeechConfig, "model_fields", {})
        if speech_language_code and "language_code" in speech_fields:
            speech_config_kwargs["language_code"] = speech_language_code
        elif speech_language_code:
            logger.warning(
                "当前 google-genai SDK 的 SpeechConfig 不支持 language_code，"
                "将仅依赖 system instruction 约束回复语言"
            )

        # 会话恢复：传入 handle 时恢复上下文；首次连接时启用 resumption 以便后续恢复
        if session_handle:
            session_resumption_cfg = types.SessionResumptionConfig(
                handle=session_handle,
            )
        elif self._config.session_resumption:
            session_resumption_cfg = types.SessionResumptionConfig(handle=None)
        else:
            session_resumption_cfg = None

        live_cfg = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(**speech_config_kwargs),
            system_instruction=system_instruction,
            input_audio_transcription=(
                types.AudioTranscriptionConfig()
                if self._config.input_transcription
                else None
            ),
            output_audio_transcription=(
                types.AudioTranscriptionConfig()
                if self._config.output_transcription
                else None
            ),
            session_resumption=session_resumption_cfg,
            context_window_compression=types.ContextWindowCompressionConfig(
                trigger_tokens=self._config.trigger_tokens,
                sliding_window=types.SlidingWindow(
                    target_tokens=self._config.target_tokens,
                ),
            ),
            # 自动 VAD 模式
            # silence_duration_ms=800: 容忍长句中自然的换气/逗号停顿，避免长句被截断
            # end_of_speech_sensitivity=LOW: 降低结束检测敏感度，减少误触发
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                    prefix_padding_ms=20,
                    silence_duration_ms=800,
                )
            ),
        )
        return live_cfg

    async def _open_gemini_session(
        self,
        *,
        client: genai.Client,
        live_config: types.LiveConnectConfig,
    ) -> tuple[Any, Any]:
        """
        打开一个 Gemini Live session，并返回 (gemini_cm, gemini_session)。

        说明：这里用 __aenter__/__aexit__ 手动管理生命周期，便于在同一 WebSocket 会话内重建连接。
        """
        gemini_cm = client.aio.live.connect(
            model=self._config.model,
            config=live_config,
        )
        gemini_session = await gemini_cm.__aenter__()
        return gemini_cm, gemini_session

    async def _close_gemini_session(self, gemini_cm: Any):
        try:
            await gemini_cm.__aexit__(None, None, None)
        except Exception as e:
            logger.debug(f"关闭 Gemini session 失败（忽略）: {e}")

    async def _reconnect_gemini_session(
        self,
        *,
        session: LiveSession,
        client: genai.Client,
        live_config: types.LiveConnectConfig,
        db: AsyncSession,
        on_audio: Callable[[bytes], Any],
        on_transcript: Callable[[str, str], Any],
        on_status: Callable[[LiveChatStatus, Optional[str]], Any],
        on_error: Callable[[str, str], Any],
        on_latency: Optional[Callable[[dict], Any]] = None,
        reason: str = "",
    ):
        """
        仅在 goAway 或异常断开时重连，使用 session_resumption 恢复对话上下文。

        与之前的"每轮重连"不同：此方法通过 SessionResumptionConfig 将之前
        捕获的 session_handle 传递给新会话，从而保留模型对对话历史的记忆。
        """
        async with session.reconnect_lock:
            async with session.gemini_lock:
                old_cm = session.gemini_cm
                old_session = session.gemini_session
                session.gemini_cm = None
                session.gemini_session = None
                old_receive_task = session.receive_task
                session.receive_task = None

            logger.debug(
                f"开始重建 Gemini Live session: reason={reason}, "
                f"next_reconnect={session.reconnect_count + 1}, "
                f"has_handle={session.session_handle is not None}"
            )

            # 用 session_resumption 恢复上下文（如果有 handle）
            if session.session_handle:
                resume_config = types.LiveConnectConfig(
                    response_modalities=live_config.response_modalities,
                    speech_config=live_config.speech_config,
                    system_instruction=live_config.system_instruction,
                    input_audio_transcription=live_config.input_audio_transcription,
                    output_audio_transcription=live_config.output_audio_transcription,
                    session_resumption=types.SessionResumptionConfig(
                        handle=session.session_handle,
                    ),
                    context_window_compression=live_config.context_window_compression,
                    realtime_input_config=live_config.realtime_input_config,
                )
            else:
                resume_config = live_config

            try:
                new_cm, new_session = await self._open_gemini_session(
                    client=client,
                    live_config=resume_config,
                )
            except Exception as e:
                await on_error("RECONNECT_ERROR", str(e))
                logger.warning(
                    f"重建 Gemini Live session 失败: reason={reason}, error={e}"
                )
                return

            # 尽量取消旧 receive_task（如果还在）
            if old_receive_task is not None:
                old_receive_task.cancel()
                try:
                    await old_receive_task
                except asyncio.CancelledError:
                    pass

            async with session.gemini_lock:
                session.gemini_cm = new_cm
                session.gemini_session = new_session
                session.reconnect_count += 1

                # 启动新的接收任务
                session.receive_task = asyncio.create_task(
                    self._receive_loop(
                        session,
                        new_session,
                        client=client,
                        live_config=live_config,
                        db=db,
                        on_audio=on_audio,
                        on_transcript=on_transcript,
                        on_status=on_status,
                        on_error=on_error,
                        on_latency=on_latency,
                    )
                )

            # 尝试把重连期间缓存的音频回放到新 session（防止用户紧接着说第二句话时丢音）
            flushed = 0
            try:
                while True:
                    try:
                        chunk = session.pending_audio.popleft()
                    except IndexError:
                        break
                    await new_session.send_realtime_input(
                        audio=types.Blob(
                            data=chunk,
                            mime_type=f"audio/pcm;rate={self._config.send_sample_rate}",
                        )
                    )
                    flushed += 1
            except Exception as e:
                logger.debug(f"flush pending audio failed（忽略）: {e}")

            # 重连成功后发送 LISTENING 状态，保持 UI 一致性
            # 不发送 CONNECTED，避免 UI 从 "聆听中" 变成 "已连接" 再变回来
            await on_status(LiveChatStatus.LISTENING, None)
            logger.debug(
                f"重建 Gemini Live session 成功: reason={reason}, "
                f"reconnect={session.reconnect_count}, flushed_audio_chunks={flushed}"
            )

            # 关闭旧 session（若存在）
            if old_cm is not None:
                await self._close_gemini_session(old_cm)

    async def start_live_session(
        self,
        session: LiveSession,
        db: AsyncSession,
        on_audio: Callable[[bytes], Any],
        on_transcript: Callable[[str, str], Any],
        on_status: Callable[[LiveChatStatus, Optional[str]], Any],
        on_error: Callable[[str, str], Any],
        on_latency: Optional[Callable[[dict], Any]] = None,
    ) -> AsyncGenerator[None, bytes]:
        """
        启动实时语音通话会话

        这是一个异步生成器，用于：
        1. 接收上行音频数据
        2. 转发到 Gemini Live
        3. 通过回调推送下行音频和转录

        Args:
            session: 会话对象
            db: 数据库会话
            on_audio: 音频回调 (data: bytes)，可以是 async 函数
            on_transcript: 转录回调 (text: str, role: 'user' | 'assistant')，可以是 async 函数
            on_status: 状态回调 (status: LiveChatStatus, message: Optional[str])，可以是 async 函数
            on_error: 错误回调 (code: str, message: str)，可以是 async 函数
            on_latency: 延迟指标回调 (latency_data: dict)，可以是 async 函数

        Yields:
            None - 通过 send() 发送上行音频数据
        """
        try:
            agent_data = await agent_service.get_agent_for_chat(
                db, agent_id=session.agent_id
            )
            if not agent_data:
                await on_error(
                    "AGENT_NOT_FOUND", f"Agent not found: {session.agent_id}"
                )
                return

            # 构建 system_instruction（文本聊天 system messages + 语言约束）
            # 预填充（prefill）仅在 enable_prefill=True 时执行，默认关闭
            prefill_turns: List[types.Content] = []
            merged_response_language_name = self._resolved_response_language_name(
                session
            )
            resolved_speech_code = self._resolved_speech_language_code(session)
            try:
                agent = await agent_manager.get_agent(agent_data)
                chat_settings = await get_or_create_chat_settings(
                    db=db,
                    chat_id=session.chat_id,
                    user_id=session.user_id,
                    agent_id=session.agent_id,
                )
                user_profile = await asyncio.to_thread(
                    agent._get_user_profile_sync, session.user_id
                )
                text_chat_system_messages = agent.build_system_messages(
                    user_profile=user_profile,
                    chat_settings=chat_settings,
                    user_time_context=None,
                    include_output_format_prompt=False,
                )
                system_instruction = (
                    self._build_system_instruction_from_text_chat_system_messages(
                        text_chat_system_messages,
                        merged_response_language_name=merged_response_language_name,
                    )
                )
                if session.config.enable_prefill:
                    history_messages = chat_history_service.get_history_messages(
                        session.session_id
                    )
                    prefill_turns = self._build_prefill_turns_from_history_messages(
                        history_messages
                    )
            except Exception as e:
                logger.warning(
                    f"构建文本聊天上下文失败，降级为旧版上下文构建: session_id={session.session_id}, error={e}"
                )
                history_messages = chat_history_service.get_history_messages(
                    session.session_id
                )
                system_instruction = self._build_system_instruction(
                    agent_data,
                    history_messages,
                    merged_response_language_name=merged_response_language_name,
                )
                if session.config.enable_prefill:
                    prefill_turns = self._build_prefill_turns_from_history_messages(
                        history_messages
                    )

            voice_id = session.config.voice_id or agent_data.get("voice_id")
            agent_gender = agent_data.get("gender")
            live_config = self._build_live_config(
                merged_speech_language_code=resolved_speech_code,
                voice_id=voice_id,
                agent_gender=agent_gender,
                system_instruction=system_instruction,
            )

            client = self._get_client()

            await on_status(LiveChatStatus.CONNECTING, "正在连接到 Gemini Live...")
            session.connect_start_time = time.time()
            gemini_cm, gemini_session = await self._open_gemini_session(
                client=client,
                live_config=live_config,
            )
            session.connect_end_time = time.time()
            session.gemini_cm = gemini_cm
            session.gemini_session = gemini_session

            if session.config.enable_prefill and prefill_turns:
                await gemini_session.send_client_content(
                    turns=prefill_turns, turn_complete=False
                )
                logger.debug(
                    f"Live 会话预填充完成: session_id={session.session_id}, turns={len(prefill_turns)}"
                )
            else:
                # 未启用预填充：直接标记完成，音频无需缓冲，直通 Gemini
                session.prefill_complete.set()

            session.status = LiveChatStatus.CONNECTED
            await on_status(LiveChatStatus.CONNECTED, "已连接")

            if on_latency and session.connect_start_time and session.connect_end_time:
                connect_latency_ms = int(
                    (session.connect_end_time - session.connect_start_time) * 1000
                )
                await on_latency({"connect_latency_ms": connect_latency_ms})

            session.receive_task = asyncio.create_task(
                self._receive_loop(
                    session,
                    gemini_session,
                    client=client,
                    live_config=live_config,
                    db=db,
                    on_audio=on_audio,
                    on_transcript=on_transcript,
                    on_status=on_status,
                    on_error=on_error,
                    on_latency=on_latency,
                )
            )

            if session.config.enable_prefill:
                # 独立任务：等待预填充完成后 flush 缓冲的音频。
                # 生成器的 yield 会阻塞等待输入，如果客户端在预填充完成前已发完所有音频，
                # 缓冲的音频将永远不会被 flush。此任务在预填充完成时主动 flush。
                async def _flush_after_prefill():
                    try:
                        await session.prefill_complete.wait()
                    except Exception:
                        return
                    async with session.gemini_lock:
                        gs = session.gemini_session
                    if gs is None:
                        return
                    if not session.pending_audio:
                        return
                    try:
                        await gs.send_realtime_input(
                            activity_start=types.ActivityStart()
                        )
                        flushed = 0
                        while True:
                            try:
                                chunk = session.pending_audio.popleft()
                            except IndexError:
                                break
                            await gs.send_realtime_input(
                                audio=types.Blob(
                                    data=chunk,
                                    mime_type=f"audio/pcm;rate={self._config.send_sample_rate}",
                                )
                            )
                            flushed += 1
                        await gs.send_realtime_input(
                            activity_end=types.ActivityEnd()
                        )
                        logger.debug(
                            f"预填充完成后 flush {flushed} 个缓冲音频包到 Gemini"
                        )
                    except Exception as e:
                        logger.debug(f"预填充 flush 失败（忽略）: {e}")

                prefill_flush_task = asyncio.create_task(_flush_after_prefill())

            try:
                logger.debug("生成器已启动，等待接收输入数据...")
                audio_count = 0
                while True:
                    input_item = yield
                    if input_item is None:
                        logger.debug("收到结束信号，停止发送")
                        break

                    item_type = (
                        input_item.get("type")
                        if isinstance(input_item, dict)
                        else "audio"
                    )

                    async with session.gemini_lock:
                        current_gemini = session.gemini_session

                    if current_gemini is None:
                        # 重连中：缓存少量音频，待重连完成后 flush
                        if item_type == "audio":
                            audio_data = (
                                input_item.get("data")
                                if isinstance(input_item, dict)
                                else input_item
                            )
                            if (
                                isinstance(audio_data, (bytes, bytearray))
                                and audio_data
                            ):
                                session.pending_audio.append(bytes(audio_data))
                                if session.config.save_history:
                                    session.conversation_audio_chunks.append(
                                        ("user", bytes(audio_data))
                                    )
                        continue

                    # 预填充尚未完成：缓冲音频，等 Gemini 就绪后由 _flush_after_prefill 任务统一 flush。
                    # 预填充期间发送到 Gemini 的音频可能被丢弃（模型还在处理上下文）。
                    if not session.prefill_complete.is_set():
                        if item_type == "audio":
                            audio_data = (
                                input_item.get("data")
                                if isinstance(input_item, dict)
                                else input_item
                            )
                            if (
                                isinstance(audio_data, (bytes, bytearray))
                                and audio_data
                            ):
                                session.pending_audio.append(bytes(audio_data))
                                if session.config.save_history:
                                    session.conversation_audio_chunks.append(
                                        ("user", bytes(audio_data))
                                    )
                        continue

                    if item_type == "activity_start":
                        await current_gemini.send_realtime_input(
                            activity_start=types.ActivityStart()
                        )
                        continue

                    if item_type == "activity_end":
                        await current_gemini.send_realtime_input(
                            activity_end=types.ActivityEnd()
                        )
                        continue

                    audio_data = (
                        input_item.get("data")
                        if isinstance(input_item, dict)
                        else input_item
                    )
                    if audio_data is None:
                        continue

                    audio_count += 1
                    session.last_audio_sent_time = time.time()
                    if session.current_turn_start_time is None:
                        session.current_turn_start_time = time.time()
                    turn_num = getattr(session, "_turn_num", 0)
                    if audio_count <= 5 or audio_count % 50 == 0:
                        logger.debug(
                            f"发送音频到 Gemini: 第 {audio_count} 个包, {len(audio_data)} bytes"
                        )

                    await current_gemini.send_realtime_input(
                        audio=types.Blob(
                            data=audio_data,
                            mime_type=f"audio/pcm;rate={self._config.send_sample_rate}",
                        )
                    )
                    if session.config.save_history:
                        session.conversation_audio_chunks.append(
                            ("user", bytes(audio_data))
                        )
            finally:
                if session.receive_task is not None:
                    session.receive_task.cancel()
                    try:
                        await session.receive_task
                    except asyncio.CancelledError:
                        pass

                if session.config.save_history:
                    await self._save_conversation_history(session, db)

                if session.gemini_cm is not None:
                    await self._close_gemini_session(session.gemini_cm)

        except Exception as e:
            logger.error(f"Live 会话错误: {str(e)}")
            await on_error("SESSION_ERROR", str(e))
            session.status = LiveChatStatus.ERROR

        finally:
            session.status = LiveChatStatus.DISCONNECTED
            await on_status(LiveChatStatus.DISCONNECTED, "会话已结束")
            self._cleanup_session(session.session_id)

    async def _receive_loop(
        self,
        session: LiveSession,
        gemini_session: Any,
        *,
        client: genai.Client,
        live_config: types.LiveConnectConfig,
        db: AsyncSession,
        on_audio: Callable[[bytes], Any],
        on_transcript: Callable[[str, str], Any],
        on_status: Callable[[LiveChatStatus, Optional[str]], Any],
        on_error: Callable[[str, str], Any],
        on_latency: Optional[Callable[[dict], Any]] = None,
    ):
        """接收 Gemini Live 响应的循环"""
        try:
            logger.debug("开始接收 Gemini Live 响应...")
            async for response in gemini_session.receive():
                logger.debug(f"收到 Gemini 响应: {type(response)}")

                # 处理 Gemini Live API 周期性返回的 token 用量统计
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    usage = response.usage_metadata
                    if hasattr(usage, "total_token_count") and usage.total_token_count:
                        session.total_token_count = usage.total_token_count
                        logger.debug(
                            f"Token 用量统计 - 总计: {usage.total_token_count} tokens"
                        )
                    if (
                        hasattr(usage, "response_tokens_details")
                        and usage.response_tokens_details
                    ):
                        for detail in usage.response_tokens_details:
                            if hasattr(detail, "modality") and hasattr(
                                detail, "token_count"
                            ):
                                modality_str = str(detail.modality)
                                session.response_token_details[modality_str] = (
                                    detail.token_count
                                )
                                logger.debug(
                                    f"  - {modality_str}: {detail.token_count} tokens"
                                )

                if (
                    hasattr(response, "session_resumption_update")
                    and response.session_resumption_update
                ):
                    update = response.session_resumption_update
                    if (
                        hasattr(update, "resumable")
                        and update.resumable
                        and hasattr(update, "new_handle")
                        and update.new_handle
                    ):
                        session.session_handle = update.new_handle
                        logger.debug(
                            f"收到会话恢复句柄: {session.session_handle[:20]}..."
                        )

                if hasattr(response, "server_content") and response.server_content:
                    server_content = response.server_content
                    logger.debug(f"收到 server_content: {type(server_content)}")

                    if (
                        hasattr(server_content, "input_transcription")
                        and server_content.input_transcription
                        and hasattr(server_content.input_transcription, "text")
                        and server_content.input_transcription.text
                    ):
                        # 运行证据：在部分模型/通道组合下，finished 可能长期为 false。
                        # 因此这里仅累计最新文本，最终在 turn_complete 时统一 flush。
                        piece = server_content.input_transcription.text or ""
                        if piece != session.last_user_transcription_piece:
                            session.pending_user_transcript = (
                                self._merge_transcription_piece(
                                    session.pending_user_transcript,
                                    piece,
                                )
                            )
                            session.last_user_transcription_piece = piece
                        session.user_transcription_updates += 1

                    if (
                        hasattr(server_content, "output_transcription")
                        and server_content.output_transcription
                        and hasattr(server_content.output_transcription, "text")
                        and server_content.output_transcription.text
                    ):
                        # 同上：只累计最新文本，最终在 turn_complete 时 flush。
                        piece = server_content.output_transcription.text or ""
                        if piece != session.last_ai_transcription_piece:
                            session.pending_ai_transcript = (
                                self._merge_transcription_piece(
                                    session.pending_ai_transcript,
                                    piece,
                                )
                            )
                            session.last_ai_transcription_piece = piece
                        session.ai_transcription_updates += 1

                    if (
                        hasattr(server_content, "model_turn")
                        and server_content.model_turn
                    ):
                        session._current_turn_has_model_response = True
                        if session.status != LiveChatStatus.SPEAKING:
                            response_after_silence_ms: Optional[int] = None
                            if session.last_audio_sent_time is not None:
                                response_after_silence_ms = int(
                                    (time.time() - session.last_audio_sent_time) * 1000
                                )
                                session.last_response_after_silence_ms = (
                                    response_after_silence_ms
                                )
                            if session.current_turn_start_time is not None:
                                turn_latency = (
                                    time.time() - session.current_turn_start_time
                                )
                                session.turn_latencies.append(turn_latency)
                                session.current_turn_start_time = None
                                if on_latency:
                                    turn_latencies_ms = [
                                        int(t * 1000) for t in session.turn_latencies
                                    ]
                                    avg_turn_latency_ms = int(
                                        sum(session.turn_latencies)
                                        / len(session.turn_latencies)
                                        * 1000
                                    )
                                    payload: Dict[str, Any] = {
                                        "turn_latencies_ms": turn_latencies_ms,
                                        "avg_turn_latency_ms": avg_turn_latency_ms,
                                    }
                                    if response_after_silence_ms is not None:
                                        payload["first_response_after_silence_ms"] = (
                                            response_after_silence_ms
                                        )
                                    await on_latency(payload)
                            session.status = LiveChatStatus.SPEAKING
                            logger.debug("发送 SPEAKING 状态到前端")
                            await on_status(LiveChatStatus.SPEAKING, None)
                        logger.debug(
                            f"AI 开始回复，parts 数量: {len(server_content.model_turn.parts)}"
                        )

                        for part in server_content.model_turn.parts:
                            if hasattr(part, "inline_data") and part.inline_data:
                                logger.debug(
                                    f"收到音频数据: {len(part.inline_data.data)} bytes"
                                )
                                if session.config.save_history:
                                    session.conversation_audio_chunks.append(
                                        ("ai", bytes(part.inline_data.data))
                                    )
                                await on_audio(part.inline_data.data)

                            # 兼容：如果未启用 output_audio_transcription，且模型确实返回文本 parts
                            if (
                                not self._config.output_transcription
                                and hasattr(part, "text")
                                and part.text
                            ):
                                session.ai_transcript_buffer += part.text
                                await on_transcript(part.text, "assistant")

                    if (
                        hasattr(server_content, "turn_complete")
                        and server_content.turn_complete
                    ):
                        had_model_turn = getattr(
                            session, "_current_turn_has_model_response", False
                        )
                        if not had_model_turn:
                            logger.debug(
                                "收到 turn_complete 但本轮无 model_turn（预填充完成信号），"
                                "保持 session 继续监听"
                            )
                            session.prefill_complete.set()
                            continue

                        # 模型真正回复了一轮：保存转录、重置状态、保持同一 session 继续监听
                        session._current_turn_has_model_response = False
                        logger.debug("AI 回复完成，发送 LISTENING 状态到前端")
                        session.status = LiveChatStatus.LISTENING
                        await on_status(LiveChatStatus.LISTENING, None)
                        session._turn_num = getattr(session, "_turn_num", 0) + 1

                        user_text = self._normalize_transcript_text(
                            session.pending_user_transcript
                        )
                        ai_text = self._normalize_transcript_text(
                            session.pending_ai_transcript
                        )

                        if user_text:
                            if session.config.save_history:
                                user_message_id = await chat_history_service.add_user_message_async(
                                    session.session_id,
                                    user_text,
                                    meta_data={
                                        "is_voice": True,
                                        "voice_session_id": session.voice_session_id,
                                    },
                                )
                                ts = time.time() * 1000
                                await on_transcript(
                                    user_text, "user", user_message_id, ts
                                )
                            else:
                                await on_transcript(user_text, "user")
                        if ai_text:
                            if session.config.save_history:
                                ai_message_id = await chat_history_service.add_ai_message_sync_async(
                                    session_id=session.session_id,
                                    message=ai_text,
                                    agent_id=session.agent_id,
                                    meta_data={
                                        "is_voice": True,
                                        "voice_session_id": session.voice_session_id,
                                    },
                                )
                                ts = time.time() * 1000
                                await on_transcript(
                                    ai_text, "assistant", ai_message_id, ts
                                )
                            else:
                                await on_transcript(ai_text, "assistant")

                        session.pending_user_transcript = ""
                        session.pending_ai_transcript = ""
                        session.user_transcription_updates = 0
                        session.ai_transcription_updates = 0
                        session.last_user_transcription_piece = ""
                        session.last_ai_transcription_piece = ""

                        if (
                            (not self._config.output_transcription)
                            and session.ai_transcript_buffer
                            and session.config.save_history
                        ):
                            await chat_history_service.add_ai_message_sync_async(
                                session_id=session.session_id,
                                message=session.ai_transcript_buffer.strip(),
                                agent_id=session.agent_id,
                                meta_data={
                                    "is_voice": True,
                                    "voice_session_id": session.voice_session_id,
                                },
                            )
                            session.ai_transcript_buffer = ""

                        # 保持同一 session 继续多轮对话，不重连。
                        # session_resumption 句柄已在上方捕获，仅在 goAway 或异常时用于恢复。

                if response.go_away:
                    logger.warning(
                        f"收到 goAway 通知，剩余时间: {response.go_away.time_left}"
                    )
                    await on_status(
                        LiveChatStatus.CONNECTED,
                        f"连接即将断开，剩余 {response.go_away.time_left} 秒",
                    )
                    # 等待 goAway 倒计时结束后，用 session_resumption 恢复会话上下文
                    await asyncio.sleep(response.go_away.time_left + 1)
                    await self._reconnect_gemini_session(
                        session=session,
                        client=client,
                        live_config=live_config,
                        db=db,
                        on_audio=on_audio,
                        on_transcript=on_transcript,
                        on_status=on_status,
                        on_error=on_error,
                        on_latency=on_latency,
                        reason="go_away",
                    )
                    return

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"接收循环错误: {str(e)}")
            await on_error("RECEIVE_ERROR", str(e))
            # 异常断开时用 session_resumption 恢复会话上下文
            try:
                await self._reconnect_gemini_session(
                    session=session,
                    client=client,
                    live_config=live_config,
                    db=db,
                    on_audio=on_audio,
                    on_transcript=on_transcript,
                    on_status=on_status,
                    on_error=on_error,
                    on_latency=on_latency,
                    reason=f"error:{e}",
                )
            except Exception as reconnect_error:
                logger.error(f"异常后重连失败: {reconnect_error}")

    async def _save_conversation_history(
        self,
        session: LiveSession,
        db: AsyncSession,
    ):
        """保存语音对话到聊天历史；若有音频则生成单路 WAV 写本地、上传 GCS、写表后删除本地文件。"""
        has_transcript = bool(
            session.user_transcript_buffer or session.ai_transcript_buffer
        )
        has_audio = bool(session.conversation_audio_chunks)
        if not has_transcript and not has_audio:
            return

        user_message_id: Optional[int] = None
        ai_message_id: Optional[int] = None

        try:
            if session.user_transcript_buffer:
                user_message_id = await chat_history_service.add_user_message_async(
                    session.session_id,
                    session.user_transcript_buffer,
                    meta_data={
                        "is_voice": True,
                        "voice_session_id": session.voice_session_id,
                    },
                )
                logger.debug(
                    f"保存用户语音转录: {session.user_transcript_buffer[:50]}..."
                )

            if session.ai_transcript_buffer:
                ai_message_id = await chat_history_service.add_ai_message_sync_async(
                    session_id=session.session_id,
                    message=session.ai_transcript_buffer,
                    agent_id=session.agent_id,
                    meta_data={
                        "is_voice": True,
                        "voice_session_id": session.voice_session_id,
                    },
                )
                logger.debug(
                    f"保存 AI 语音转录: {session.ai_transcript_buffer[:50]}..."
                )

        except Exception as e:
            logger.error(f"保存对话历史失败: {str(e)}")
            return

        if not has_audio:
            return

        if user_message_id is None:
            user_message_id = await chat_history_service.get_latest_user_message_id(
                db, session.session_id
            )
        if ai_message_id is None:
            ai_message_id = await chat_history_service.get_latest_ai_message_id(
                db, session.session_id
            )

        temp_path: Optional[Path] = None
        try:
            pcm_24k = build_interleaved_pcm_24k(
                session.conversation_audio_chunks,
                user_sample_rate=self._config.send_sample_rate,
                ai_sample_rate=self._config.receive_sample_rate,
            )
            if not pcm_24k:
                return
            wav_bytes = voice_tts_api.pcm_to_wav(
                pcm_24k, mime_type="audio/L16;rate=24000"
            )
            temp_dir = self._config.audio_temp_dir or tempfile.gettempdir()
            temp_path = Path(temp_dir) / (
                f"live_chat_{session.session_id}_{uuid.uuid4().hex}.wav"
            )
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_bytes(wav_bytes)

            gcs_service = GCSService()
            gcs_url = await gcs_service.upload_live_chat_audio(
                str(session.user_id),
                session.agent_id,
                session.session_id,
                session.voice_session_id,
                wav_bytes,
            )
            if not gcs_url:
                logger.warning("Live chat 音频上传 GCS 未返回 URL，跳过写表")
                return

            total_duration = len(pcm_24k) / (self._config.receive_sample_rate * 2)
            if user_message_id is not None:
                await chat_history_service.update_message_audio_url(
                    db,
                    session.session_id,
                    str(user_message_id),
                    gcs_url,
                    audio_duration=total_duration,
                )
            if ai_message_id is not None:
                await chat_history_service.update_message_audio_url(
                    db,
                    session.session_id,
                    str(ai_message_id),
                    gcs_url,
                    audio_duration=total_duration,
                )
        except Exception as e:
            logger.error(f"保存 live chat 音频到 GCS 失败: {str(e)}")
        finally:
            if temp_path is not None and temp_path.exists():
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError as e:
                    logger.debug(f"删除临时文件失败（忽略）: {e}")

    def _cleanup_session(self, session_id: str):
        """清理会话"""
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
            logger.debug(f"清理会话: {session_id}")

    async def send_audio(
        self,
        session_id: str,
        audio_data: bytes,
    ):
        """发送音频数据到 Gemini Live"""
        session = self._active_sessions.get(session_id)
        if not session or not session.gemini_session:
            raise ValueError(f"Session not found or not connected: {session_id}")

        await session.gemini_session.send_realtime_input(
            audio=types.Blob(
                data=audio_data,
                mime_type=f"audio/pcm;rate={self._config.send_sample_rate}",
            )
        )

    async def send_activity_start(self, session_id: str):
        session = self._active_sessions.get(session_id)
        if not session or not session.gemini_session:
            raise ValueError(f"Session not found or not connected: {session_id}")
        await session.gemini_session.send_realtime_input(
            activity_start=types.ActivityStart()
        )

    async def send_activity_end(self, session_id: str):
        session = self._active_sessions.get(session_id)
        if not session or not session.gemini_session:
            raise ValueError(f"Session not found or not connected: {session_id}")
        await session.gemini_session.send_realtime_input(
            activity_end=types.ActivityEnd()
        )

    async def send_text(
        self,
        session_id: str,
        text: str,
    ):
        """发送文本消息到 Gemini Live"""
        session = self._active_sessions.get(session_id)
        if not session or not session.gemini_session:
            raise ValueError(f"Session not found or not connected: {session_id}")

        await session.gemini_session.send(
            input=types.Content(
                role="user",
                parts=[types.Part(text=text)],
            ),
            end_of_turn=True,
        )

        session.user_transcript_buffer += f" {text}"

    async def end_session(self, session_id: str):
        """结束会话"""
        session = self._active_sessions.get(session_id)
        if session:
            session.status = LiveChatStatus.DISCONNECTED
            self._cleanup_session(session_id)
            logger.info(f"会话已结束: {session_id}")

    def get_session(self, session_id: str) -> Optional[LiveSession]:
        """获取会话"""
        return self._active_sessions.get(session_id)

    def is_enabled(self) -> bool:
        """检查功能是否启用"""
        return self._config.enabled


live_chat_service = LiveChatService()
