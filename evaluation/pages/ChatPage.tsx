/**
 * 单角色聊天页面
 * 提供与单个智能体的实时聊天功能
 */

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Layout,
  Card,
  Input,
  Button,
  List,
  Avatar,
  Space,
  Typography,
  Spin,
  Modal,
  Tooltip,
  Tag,
  Row,
  Col,
  Empty,
  message,
  Image,
} from "antd";
import {
  SendOutlined,
  UserOutlined,
  ClearOutlined,
  DownloadOutlined,
  ClockCircleOutlined,
  HistoryOutlined,
  RedoOutlined,
  DeleteOutlined,
  LikeOutlined,
  DislikeOutlined,
  CrownOutlined,
} from "@ant-design/icons";
import { useApiKeyContext } from "../hooks/useApiKey";
import api from "../services/api";
import type { Agent, FestivalMemoryItem } from "../types";
import VoicePlayer from "../components/common/VoicePlayer";
import { PremiumModeToggle } from "../components/common/PremiumModeToggle";
import { ChatModeSelector } from "../components/common/ChatModeSelector";
import { AvatarDisplay } from "../components/common/AvatarDisplay";
import { SingleAgentSelectorPanel } from "../components/common/SingleAgentSelectorPanel";
import AgentDetailModal from "../components/common/AgentDetailModal";
import { MessageToImageIcon } from "../components/MessageToImageIcon";
import {
  formatUtcTimeOnly,
  formatUtcTimeRaw,
  getCurrentUtcTime,
} from "../utils/dateUtils";
import {
  IMAGE_FEEDBACK_PROMPT_LAST_DATE_KEY,
  shouldShowImageFeedbackPrompt,
  toLocalCalendarDateKey,
} from "../utils/imageFeedbackPromptGate";
import { buildImageFeedbackTargetId } from "../utils/imageFeedbackReport";

const { Content } = Layout;
const { Text, Paragraph } = Typography;
const { TextArea } = Input;

interface ChatSession {
  id: string;
  agent_id: string;
  agent_name: string;
  messages: ChatMessage[];
  created_at: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant"; // 与API返回的role字段一致，值为 'user' 或 'assistant'
  content: string;
  timestamp: string;
  remoteId?: string; // 数据库消息ID，用于删除和重发功能
  /** 服务端消息列表 / completions 回显的客户端本地 id（对齐乐观 UI） */
  local_id?: string;
  type?: "text" | "image" | "festival_memory_prompt" | "surprise_snap"; // 消息类型：文本、图片、节日记忆提示、Surprise Snap
  festival_memory_id?: number; // 节日记忆提示消息对应的 memory 记录 id（仅 type=festival_memory_prompt 时）
  image_url?: string; // 图片URL（仅图片消息）
  // Surprise Snap 专属角色照（仅 type=surprise_snap 时）
  media_url?: string;
  caption?: string;
  price?: number;
  is_locked?: boolean;
  user_vote?: "like" | "dislike" | null; // 用户投票：点赞/点踩
  meta_data?: {
    messageType?: string;
    agentId?: string;
    generated_image?: {
      image_url: string;
      width: number;
      height: number;
      prompt?: string;
      // 匹配图片相关字段
      is_matched?: boolean;
      similarity?: number;
      matched_from_user_id?: string;
      // 生成耗时和模型信息
      model?: string;
      generation_time_ms?: number;
    };
  };
}

interface PendingImageFeedback {
  imageUrl: string;
  vote: "like" | "dislike";
}

export const ChatPage: React.FC = () => {
  // 状态管理
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(
    null,
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [sending, setSending] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatSession[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [generatedImages, setGeneratedImages] = useState<Map<string, string>>(
    new Map(),
  );
  const [pendingImageFeedback, setPendingImageFeedback] =
    useState<PendingImageFeedback | null>(null);
  const [imageFeedbackFormVisible, setImageFeedbackFormVisible] =
    useState(false);
  const [imageFeedbackText, setImageFeedbackText] = useState("");
  const [submittingImageFeedback, setSubmittingImageFeedback] = useState(false);
  const [festivalMemoryModalOpen, setFestivalMemoryModalOpen] = useState(false);
  const [agentWithFestivalMemories, setAgentWithFestivalMemories] =
    useState<Agent | null>(null);
  const [festivalMemoriesLoading, setFestivalMemoriesLoading] = useState(false);
  const [agentDetailModalVisible, setAgentDetailModalVisible] = useState(false);
  const [userProfile, setUserProfile] = useState<{
    is_superuser?: boolean;
  } | null>(null);
  const [subscriptionStatus, setSubscriptionStatus] = useState<{
    is_subscribed?: boolean;
  } | null>(null);
  const backgroundImageUrl = selectedAgent?.background;
  const backgroundAnimatedUrl = selectedAgent?.background_animated;
  const backgroundAltName = selectedAgent?.name ?? "角色";
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const isSurpriseSnapMessage = (m: ChatMessage) =>
    m.type === "surprise_snap" || m.meta_data?.messageType === "surprise_snap";

  const { isApiKeyValid } = useApiKeyContext();

  // 获取当前用户 profile 与订阅状态（用于 Surprise Snap 前端展示：订阅/管理员仍显示图片）
  useEffect(() => {
    if (!isApiKeyValid) {
      setUserProfile(null);
      setSubscriptionStatus(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [profileRes, subRes] = await Promise.all([
          api.users.me(),
          api.subscription.getStatus(),
        ]);
        if (cancelled) return;
        const data = profileRes as { is_superuser?: boolean };
        const subData = subRes as { is_subscribed?: boolean };
        setUserProfile(data ? { is_superuser: data.is_superuser } : null);
        setSubscriptionStatus(
          subData ? { is_subscribed: subData.is_subscribed } : null,
        );
      } catch {
        if (!cancelled) {
          setUserProfile(null);
          setSubscriptionStatus(null);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isApiKeyValid]);

  // 从localStorage加载已生成的图片
  useEffect(() => {
    const savedImages = localStorage.getItem("generatedImages");
    if (savedImages) {
      try {
        const parsedImages = JSON.parse(savedImages);
        setGeneratedImages(new Map(Object.entries(parsedImages)));
      } catch (error) {
        console.error("Failed to parse saved images:", error);
      }
    }
  }, []);

  // 点开特殊消息（静静查看）时调用 agent info（GET /ai/agents/:id）获取 features 并展示节日记忆
  useEffect(() => {
    if (!festivalMemoryModalOpen || !selectedAgent?.id) {
      setAgentWithFestivalMemories(null);
      return;
    }
    setFestivalMemoriesLoading(true);
    api.agents
      .get(selectedAgent.id)
      .then((agent) => {
        setAgentWithFestivalMemories(agent);
      })
      .finally(() => {
        setFestivalMemoriesLoading(false);
      });
  }, [festivalMemoryModalOpen, selectedAgent?.id]);

  // 重新发送和删除消息相关状态
  const [resending, setResending] = useState<string | null>(null);
  const [clearing, setClearing] = useState<string | null>(null);

  // 获取最后一条有效的AI消息的索引
  const getLastAssistantMessageIndex = useCallback(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      if (
        msg.role === "assistant" &&
        msg.remoteId &&
        !msg.remoteId.startsWith("assistant_") &&
        !msg.remoteId.startsWith("error_") &&
        !msg.remoteId.startsWith("remote_")
      ) {
        return i;
      }
    }
    return -1;
  }, [messages]);

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // 滚动到底部当消息更新时
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // GEMINI: 消息发送完毕后，自动聚焦输入框
  useEffect(() => {
    if (!sending && inputRef.current) {
      inputRef.current.focus();
    }
  }, [sending]);

  // 加载聊天历史
  const loadChatHistory = useCallback(async () => {
    try {
      const history = localStorage.getItem("chat_history");
      if (history) {
        setChatHistory(JSON.parse(history));
      }
    } catch (error) {
      console.error("加载聊天历史失败:", error);
    }
  }, []);

  // 保存聊天历史
  const saveChatHistory = useCallback((sessions: ChatSession[]) => {
    try {
      localStorage.setItem("chat_history", JSON.stringify(sessions));
    } catch (error) {
      console.error("保存聊天历史失败:", error);
    }
  }, []);

  // 显示聊天历史 - 拉取最新的聊天记录
  const handleShowChatHistory = useCallback(async () => {
    if (!selectedAgent?.id) {
      message.warning("请先选择一个智能体");
      return;
    }

    setHistoryLoading(true);
    try {
      // 调用 chatApi.getMessages() 拉取全部的聊天记录
      const messagesData = await api.chat.getMessages(selectedAgent.id, {
        page: 1,
        size: 1000, // 设置较大的size来获取更多消息
      });

      if (messagesData.messages && messagesData.messages.length > 0) {
        // 转换消息格式（支持文本和图片消息）
        const convertedMessages: ChatMessage[] = messagesData.messages.map(
          (msg, index) => ({
            id: `msg_history_${index}_${Date.now()}`,
            role:
              msg.type === "festival_memory_prompt" ||
              msg.type === "surprise_snap"
                ? "assistant"
                : (msg.role ?? "assistant"),
            content: msg.content || "",
            timestamp: msg.timestamp,
            remoteId: msg.id.toString(),
            type: msg.type || "text",
            festival_memory_id: msg.festival_memory_id,
            image_url: msg.image_url,
            media_url: msg.media_url,
            caption: msg.caption,
            price: msg.price,
            is_locked: msg.is_locked,
            user_vote: msg.user_vote || null,
            local_id: msg.local_id,
            meta_data: msg.meta_data,
          }),
        );

        // 去重：根据 remoteId 去除重复消息
        const uniqueMessages = convertedMessages.filter(
          (msg, index, self) =>
            index === self.findIndex((m) => m.remoteId === msg.remoteId),
        );

        console.log(
          `获取到 ${convertedMessages.length} 条消息，去重后 ${uniqueMessages.length} 条`,
        );

        // 更新当前会话的消息
        setMessages(uniqueMessages);

        // 更新当前会话
        if (currentSession) {
          const updatedSession = {
            ...currentSession,
            messages: uniqueMessages,
          };
          setCurrentSession(updatedSession);

          // 更新本地历史记录
          const updatedHistory = chatHistory.map((session) =>
            session.id === currentSession.id ? updatedSession : session,
          );
          setChatHistory(updatedHistory);
          saveChatHistory(updatedHistory);
        }

        message.success(`成功获取 ${uniqueMessages.length} 条聊天记录`);
      } else {
        message.info("暂无聊天记录");
      }

      // 显示聊天历史模态框
      setShowHistory(true);
    } catch (error) {
      console.error("获取聊天记录失败:", error);
      message.error("获取聊天记录失败，请重试");
    } finally {
      setHistoryLoading(false);
    }
  }, [selectedAgent?.id, currentSession, chatHistory, saveChatHistory]);

  // 初始化加载历史
  useEffect(() => {
    loadChatHistory();
  }, [loadChatHistory]);

  // 处理消息投票（点赞/点踩）
  const maybePromptImageFeedback = useCallback(
    (msg: ChatMessage, vote: "like" | "dislike" | null) => {
      if (vote === null) {
        return;
      }
      const imageUrl = msg.meta_data?.generated_image?.image_url;
      if (!imageUrl) {
        return;
      }
      const now = new Date();
      const lastShownDate = localStorage.getItem(
        IMAGE_FEEDBACK_PROMPT_LAST_DATE_KEY,
      );
      if (!shouldShowImageFeedbackPrompt(lastShownDate, now)) {
        return;
      }
      localStorage.setItem(
        IMAGE_FEEDBACK_PROMPT_LAST_DATE_KEY,
        toLocalCalendarDateKey(now),
      );
      Modal.confirm({
        title: "请给这张图片一点反馈",
        content: "每天最多弹一次。点击“去反馈”后会自动带上图片 URL。",
        okText: "去反馈",
        cancelText: "暂不反馈",
        onOk: () => {
          setPendingImageFeedback({ imageUrl, vote });
          setImageFeedbackText("");
          setImageFeedbackFormVisible(true);
        },
      });
    },
    [],
  );

  const handleSubmitImageFeedback = useCallback(async () => {
    if (!pendingImageFeedback) {
      return;
    }
    setSubmittingImageFeedback(true);
    try {
      const trimmedFeedbackText = imageFeedbackText.trim();
      const description =
        `[IMAGE_FEEDBACK][vote=${pendingImageFeedback.vote}] ${trimmedFeedbackText}`.trim();
      await api.report.create({
        target_id: buildImageFeedbackTargetId(pendingImageFeedback.imageUrl),
        target_type: "USER",
        reason_codes: ["OTHER"],
        image_urls: [pendingImageFeedback.imageUrl],
        description,
        report_type: "FEEDBACK",
      });
      message.success("图片反馈已提交");
      setImageFeedbackFormVisible(false);
      setPendingImageFeedback(null);
      setImageFeedbackText("");
    } catch (error) {
      console.error("提交图片反馈失败:", error);
      message.error("提交失败，请稍后重试");
    } finally {
      setSubmittingImageFeedback(false);
    }
  }, [imageFeedbackText, pendingImageFeedback]);

  const handleMessageVote = useCallback(
    async (msg: ChatMessage, newVote: "like" | "dislike" | null) => {
      if (!selectedAgent?.id || !msg.remoteId) {
        message.warning("无法更新投票：缺少必要信息");
        return;
      }

      // 验证 remoteId 是否为有效数字
      const messageId = parseInt(msg.remoteId);
      if (isNaN(messageId)) {
        message.warning("无法更新投票：消息ID无效");
        return;
      }

      // 确定新的投票状态
      let finalVote: "like" | "dislike" | null = newVote;
      const currentVote = msg.user_vote;

      // 实现切换逻辑：
      // - 未投票 → 点赞
      // - 点赞 → 点踩（如果点击点踩）或取消（如果再次点击点赞）
      // - 点踩 → 点赞（如果点击点赞）或取消（如果再次点击点踩）
      if (currentVote === null) {
        // 未投票，设置为新投票
        finalVote = newVote;
      } else if (currentVote === "like") {
        // 当前是点赞
        if (newVote === "like") {
          // 再次点击点赞，取消投票
          finalVote = null;
        } else {
          // 点击点踩，切换到点踩
          finalVote = "dislike";
        }
      } else if (currentVote === "dislike") {
        // 当前是点踩
        if (newVote === "dislike") {
          // 再次点击点踩，取消投票
          finalVote = null;
        } else {
          // 点击点赞，切换到点赞
          finalVote = "like";
        }
      }

      // 乐观更新：先更新 UI（使用函数式更新，避免闭包问题）
      setMessages((prevMessages) => {
        if (!prevMessages || prevMessages.length === 0) {
          console.warn("警告：尝试更新投票时消息列表为空，跳过更新");
          return prevMessages || [];
        }
        const updated = prevMessages.map((m) =>
          m.remoteId === msg.remoteId ? { ...m, user_vote: finalVote } : m,
        );
        console.log("乐观更新消息投票:", {
          messageId: msg.remoteId,
          currentVote,
          finalVote,
          messagesCount: prevMessages.length,
          updatedCount: updated.length,
        });
        // 确保返回的数组不为空
        if (updated.length === 0) {
          console.error("错误：更新后消息列表为空，返回原始列表");
          return prevMessages;
        }
        return updated;
      });

      try {
        // 调用 API 更新投票
        const response = await api.chat.updateMessageVote(
          selectedAgent.id,
          messageId,
          finalVote,
        );
        console.log("投票更新成功:", response);
        message.success(
          finalVote === null
            ? "已取消投票"
            : finalVote === "like"
              ? "已点赞"
              : "已点踩",
        );
        maybePromptImageFeedback(msg, finalVote);
      } catch (error) {
        console.error("更新投票失败:", error, {
          messageId: msg.remoteId,
          agentId: selectedAgent?.id,
        });
        // 回滚 UI 更新：恢复原始消息状态
        setMessages((prevMessages) => {
          if (!prevMessages || prevMessages.length === 0) {
            console.error("错误：回滚时消息列表为空，无法回滚");
            return prevMessages || [];
          }
          const rolledBack = prevMessages.map((m) =>
            m.remoteId === msg.remoteId ? { ...m, user_vote: currentVote } : m,
          );
          // 确保回滚后不为空
          if (rolledBack.length === 0) {
            console.error("错误：回滚后消息列表为空，返回原始列表");
            return prevMessages;
          }
          return rolledBack;
        });
        message.error("更新投票失败，请重试");
      }
    },
    [maybePromptImageFeedback, selectedAgent?.id],
  );

  const [unlockingSurpriseSnapId, setUnlockingSurpriseSnapId] = useState<
    number | null
  >(null);

  const handleSurpriseSnapUnlock = useCallback(
    async (messageId: number) => {
      if (!selectedAgent) return;
      setUnlockingSurpriseSnapId(messageId);
      try {
        await api.chat.surpriseSnapUnlock(messageId);
        const messagesResponse = await api.chat.getMessages(selectedAgent.id, {
          limit: 100,
          offset: 0,
        });
        const msgList = messagesResponse.messages ?? [];
        const converted: ChatMessage[] = msgList.map((msg, i) => ({
          id: `msg_${selectedAgent.id}_${i}_${Date.now()}`,
          role:
            msg.type === "festival_memory_prompt" &&
            (msg.role == null || String(msg.role) === "")
              ? "assistant"
              : (msg.role ??
                (msg.sender_type === "USER" ? "user" : "assistant")),
          content: msg.content || "",
          timestamp:
            msg.timestamp || msg.created_at || new Date().toISOString(),
          remoteId: msg.id ? msg.id.toString() : undefined,
          type: msg.type || "text",
          festival_memory_id: msg.festival_memory_id,
          image_url: msg.image_url,
          media_url: msg.media_url,
          caption: msg.caption,
          price: msg.price,
          is_locked: msg.is_locked,
          user_vote: msg.user_vote || null,
          local_id: msg.local_id,
          meta_data: msg.meta_data,
        }));
        const unique = converted.filter(
          (msg, index, self) =>
            msg.remoteId &&
            index === self.findIndex((m) => m.remoteId === msg.remoteId),
        );
        setMessages(unique);
      } catch (e) {
        console.error("Surprise Snap 解锁失败:", e);
        message.error("解锁失败，请重试");
      } finally {
        setUnlockingSurpriseSnapId(null);
      }
    },
    [selectedAgent],
  );

  // 选择智能体 - 从后端获取真实会话记录
  const handleSelectAgent = useCallback(
    async (agent: Agent) => {
      setSelectedAgent(agent);
      setSending(true);

      try {
        const currentSettings = await api.chat.getAgentSettings(agent.id);
        console.log(`智能体 ${agent.name} 的当前聊天设置:`, currentSettings);
        // 使用聊天消息接口获取历史（GET /chats/agents/{agent_id}/messages）
        const messagesResponse = await api.chat.getMessages(agent.id, {
          limit: 100,
          offset: 0,
        });

        const msgList = messagesResponse.messages ?? [];

        // 转换消息格式（支持文本和图片消息）
        const convertedMessages: ChatMessage[] = msgList.map((msg, index) => ({
          id: `msg_${agent.id}_${index}_${Date.now()}`,
          role:
            msg.type === "festival_memory_prompt" ||
            msg.type === "surprise_snap"
              ? "assistant"
              : (msg.role ??
                (msg.sender_type === "USER" ? "user" : "assistant")), // 后端 surprise_snap 返回 role=null，前端强制为 assistant 以正确展示
          content: msg.content || "",
          timestamp:
            msg.timestamp || msg.created_at || new Date().toISOString(),
          remoteId: msg.id ? msg.id.toString() : undefined, // 使用真实消息ID
          type: msg.type || "text",
          festival_memory_id: msg.festival_memory_id,
          image_url: msg.image_url,
          media_url: msg.media_url,
          caption: msg.caption,
          price: msg.price,
          is_locked: msg.is_locked,
          user_vote: msg.user_vote || null,
          local_id: msg.local_id,
          meta_data: msg.meta_data,
        }));

        console.log("获取到的消息数量:", msgList.length);
        if (msgList.length > 0) {
          console.log("第一条消息示例:", msgList[0]);
        }
        console.log("转换后的消息:", convertedMessages);

        // 去重：根据 remoteId 去除重复消息
        const uniqueMessages = convertedMessages.filter(
          (msg, index, self) =>
            msg.remoteId &&
            index === self.findIndex((m) => m.remoteId === msg.remoteId),
        );

        console.log(`去重后消息数量: ${uniqueMessages.length}`);
        console.log(
          "用户消息数量:",
          uniqueMessages.filter((m) => m.role === "user").length,
        );
        console.log(
          "AI消息数量:",
          uniqueMessages.filter((m) => m.role === "assistant").length,
        );
        console.log(
          "图片消息数量:",
          uniqueMessages.filter((m) => m.type === "image").length,
        );

        // 创建会话对象（消息接口不返回 chat_info，使用 agent 维度的临时 id）
        const session: ChatSession = {
          id: `temp_${agent.id}`,
          agent_id: agent.id,
          agent_name: agent.name,
          messages: uniqueMessages,
          created_at: new Date().toISOString(),
        };

        setCurrentSession(session);
        setMessages(uniqueMessages);

        // 更新本地历史记录缓存
        const existingHistoryIndex = chatHistory.findIndex(
          (s) => s.agent_id === agent.id,
        );
        let updatedHistory;
        if (existingHistoryIndex >= 0) {
          // 更新现有记录
          updatedHistory = [...chatHistory];
          updatedHistory[existingHistoryIndex] = session;
        } else {
          // 添加新记录到开头
          updatedHistory = [session, ...chatHistory];
        }
        setChatHistory(updatedHistory);
        saveChatHistory(updatedHistory);

        console.log(
          `成功加载智能体 ${agent.name} 的聊天记录，共 ${convertedMessages.length} 条消息`,
        );
      } catch (error) {
        console.error("加载聊天会话失败:", error);

        // 如果获取失败，不要创建新会话，直接使用本地临时会话
        // 避免因为已存在会话导致的唯一约束错误
        const tempSession: ChatSession = {
          id: `temp_${Date.now()}`,
          agent_id: agent.id,
          agent_name: agent.name,
          messages: [],
          created_at: new Date().toISOString(),
        };

        setCurrentSession(tempSession);
        setMessages([]);

        console.log(`为智能体 ${agent.name} 创建了本地临时会话`);

        // 后台尝试获取历史消息，但不影响当前操作
        try {
          const historyData = await api.chat.getMessages(agent.id, {
            page: 1,
            size: 100,
          });
          if (historyData.messages && historyData.messages.length > 0) {
            const convertedMessages: ChatMessage[] = historyData.messages.map(
              (msg, index) => ({
                id: `msg_history_${index}_${Date.now()}`,
                role:
                  msg.type === "festival_memory_prompt" ||
                  msg.type === "surprise_snap"
                    ? "assistant"
                    : (msg.role ?? "assistant"),
                content: msg.content || "",
                timestamp: msg.timestamp,
                remoteId: msg.id ? String(msg.id) : `remote_${index}`, // 安全地访问id字段
                type: msg.type || "text",
                festival_memory_id: msg.festival_memory_id,
                image_url: msg.image_url,
                media_url: msg.media_url,
                caption: msg.caption,
                price: msg.price,
                is_locked: msg.is_locked,
                user_vote: msg.user_vote || null,
                local_id: msg.local_id,
                meta_data: msg.meta_data,
              }),
            );

            // 去重：根据 remoteId 去除重复消息
            const uniqueMessages = convertedMessages.filter(
              (msg, index, self) =>
                index === self.findIndex((m) => m.remoteId === msg.remoteId),
            );

            setMessages(uniqueMessages.reverse()); // 反转顺序，最新的在底部
            console.log(
              `成功加载智能体 ${agent.name} 的历史消息，共 ${uniqueMessages.length} 条（原始 ${convertedMessages.length} 条）`,
            );
          }
        } catch (historyError) {
          console.error("加载历史消息失败，继续使用空会话:", historyError);
        }
      } finally {
        setSending(false);
      }
    },
    [chatHistory, saveChatHistory],
  );

  // 发送消息 - 使用现有聊天API
  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || !selectedAgent || !currentSession || sending) {
      return;
    }

    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: "user",
      content: inputValue.trim(),
      timestamp: new Date().toISOString(),
      remoteId: `user_${Date.now()}`, // 为用户消息添加临时 remoteId
    };

    // 添加用户消息到UI
    const messagesWithUser = [...messages, userMessage];
    setMessages(messagesWithUser);
    setInputValue("");
    setSending(true);

    try {
      // 构造OpenAI格式的消息历史
      const messageHistory = messagesWithUser.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));

      // 调用现有的OpenAI兼容聊天API
      const response = await api.chat.sendMessage(
        selectedAgent.id,
        messageHistory,
        false,
        { localId: userMessage.id },
      );

      // 提取助手回复
      const assistantContent =
        response.choices[0]?.message?.content || "抱歉，我现在无法回复。";

      const assistantMessage: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: "assistant",
        content: assistantContent,
        timestamp: new Date().toISOString(),
        remoteId: `assistant_${Date.now() + 1}`, // 为AI消息添加临时 remoteId
      };

      const finalMessages = [...messagesWithUser, assistantMessage];
      setMessages(finalMessages);

      // 发送成功后，刷新聊天记录以获取真实的消息ID
      try {
        // 等待一小段时间确保后端处理完成
        await new Promise((resolve) => setTimeout(resolve, 500));

        // 重新获取最新的聊天记录
        const refreshedData = await api.chat.getMessages(selectedAgent.id, {
          page: 1,
          size: 100,
        });

        if (refreshedData.messages && refreshedData.messages.length > 0) {
          const refreshedMessages: ChatMessage[] = refreshedData.messages.map(
            (msg, index) => ({
              id: `msg_refreshed_${index}_${Date.now()}`,
              role:
                msg.type === "festival_memory_prompt" ||
                msg.type === "surprise_snap"
                  ? "assistant"
                  : (msg.role ?? "assistant"),
              content: msg.content || "",
              timestamp: msg.timestamp,
              remoteId: msg.id ? String(msg.id) : `remote_${index}`,
              type: msg.type || "text",
              festival_memory_id: msg.festival_memory_id,
              image_url: msg.image_url,
              media_url: msg.media_url,
              caption: msg.caption,
              price: msg.price,
              is_locked: msg.is_locked,
              user_vote: msg.user_vote || null,
              local_id: msg.local_id,
              meta_data: msg.meta_data,
            }),
          );

          // 去重：根据 remoteId 去除重复消息
          const uniqueMessages = refreshedMessages.filter(
            (msg, index, self) =>
              index === self.findIndex((m) => m.remoteId === msg.remoteId),
          );

          console.log(
            `刷新消息：原始 ${refreshedMessages.length} 条，去重后 ${uniqueMessages.length} 条`,
          );

          // 更新消息列表（最新的在底部）
          setMessages(uniqueMessages.reverse());

          // 更新会话
          const updatedSession = {
            ...currentSession,
            messages: uniqueMessages,
          };
          setCurrentSession(updatedSession);

          // 更新历史记录
          const updatedHistory = chatHistory.map((session) =>
            session.id === currentSession.id ? updatedSession : session,
          );
          setChatHistory(updatedHistory);
          saveChatHistory(updatedHistory);

          console.log("已刷新聊天记录，获取到真实消息ID");
        }
      } catch (refreshError) {
        console.warn("刷新聊天记录失败，但消息发送成功:", refreshError);

        // 如果刷新失败，仍然保留原来的逻辑
        const updatedSession = {
          ...currentSession,
          messages: finalMessages,
        };
        setCurrentSession(updatedSession);

        const updatedHistory = chatHistory.map((session) =>
          session.id === currentSession.id ? updatedSession : session,
        );
        setChatHistory(updatedHistory);
        saveChatHistory(updatedHistory);
      }
    } catch (error) {
      console.error("发送消息失败:", error);

      // 添加错误消息
      const errorMessage: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: "assistant",
        content: "抱歉，我现在无法回复。请稍后再试。",
        timestamp: new Date().toISOString(),
        remoteId: `error_${Date.now() + 1}`, // 为错误消息添加 remoteId
      };

      const finalMessages = [...messagesWithUser, errorMessage];
      setMessages(finalMessages);
    } finally {
      setSending(false);
    }
  }, [
    inputValue,
    selectedAgent,
    currentSession,
    messages,
    sending,
    chatHistory,
    saveChatHistory,
  ]);

  // 清空聊天记录 - 使用现有聊天API
  const handleClearChat = useCallback(() => {
    if (!currentSession || !selectedAgent) return;

    Modal.confirm({
      title: "确认清空",
      content: "确定要清空当前聊天记录吗？此操作不可恢复。",
      okText: "确定",
      cancelText: "取消",
      onOk: async () => {
        try {
          // 先获取当前消息列表，找到第一个可用的消息ID
          const currentMessages = await api.chat.getMessages(selectedAgent.id, {
            page: 1,
            size: 10,
          });
          console.log(`currentMessages: ${JSON.stringify(currentMessages)}`);

          if (
            currentMessages.messages &&
            currentMessages.messages.length >= 2
          ) {
            // 消息顺序是最新到最旧，找出目前消息列表中倒数第 2 个用户消息的 ID
            const firstUserMsgId =
              currentMessages.messages[currentMessages.messages.length - 2].id;
            console.log(`firstUserMsgId: ${firstUserMsgId}`);
            await api.chat.clearMessages(
              selectedAgent.id,
              firstUserMsgId.toString(),
            );
          }
          const refreshedMessages = await api.chat.getMessages(
            selectedAgent.id,
            {
              page: 1,
              size: 100,
            },
          );
          const convertedMessages: ChatMessage[] = (
            refreshedMessages.messages || []
          ).map((msg) => ({
            id: msg.id.toString(), // 转换number到string
            role:
              msg.type === "festival_memory_prompt" ||
              msg.type === "surprise_snap"
                ? "assistant"
                : (msg.role ?? "assistant"),
            content: msg.content,
            timestamp: msg.timestamp,
            remoteId: msg.id.toString(), // 添加remoteId
            type: msg.type || "text",
            festival_memory_id: msg.festival_memory_id,
            image_url: msg.image_url,
            media_url: msg.media_url,
            caption: msg.caption,
            price: msg.price,
            is_locked: msg.is_locked,
            user_vote: msg.user_vote || null,
            local_id: msg.local_id,
            meta_data: msg.meta_data,
          }));

          // 去重：根据 remoteId 去除重复消息
          const uniqueMessages = convertedMessages.filter(
            (msg, index, self) =>
              index === self.findIndex((m) => m.remoteId === msg.remoteId),
          );

          console.log(
            `清除消息后刷新：原始 ${convertedMessages.length} 条，去重后 ${uniqueMessages.length} 条`,
          );

          setMessages(uniqueMessages);

          const updatedSession = {
            ...currentSession,
            messages: uniqueMessages,
          };
          setCurrentSession(updatedSession);

          const updatedHistory = chatHistory.map((session) =>
            session.id === currentSession.id ? updatedSession : session,
          );
          setChatHistory(updatedHistory);
          saveChatHistory(updatedHistory);

          message.success("聊天记录已清空，开场白已保留");
        } catch (error) {
          console.error("清空聊天记录失败:", error);
          let errorMessage = "清空聊天记录失败，请重试。";
          let errorDetail: unknown = null;

          // Check if it's our custom ApiError
          if (error instanceof Error && "errorData" in error) {
            // Use 'in' operator for type narrowing
            const apiError = error as { errorData: unknown; message: string }; // Cast to access errorData
            errorMessage = apiError.message;
            errorDetail = apiError.errorData;
          } else if (error instanceof Error) {
            errorMessage = error.message;
          }

          Modal.error({
            title: "清空聊天记录失败",
            content: (
              <div>
                <p>{errorMessage}</p>
                {errorDetail ? (
                  <div>
                    <p>后端返回详情:</p>
                    <pre
                      style={{
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-all",
                        maxHeight: "300px",
                        overflowY: "auto",
                        background: "#f5f5f5",
                        padding: "10px",
                        borderRadius: "4px",
                      }}
                    >
                      {JSON.stringify(
                        errorDetail as Record<string, unknown>,
                        null,
                        2,
                      )}
                    </pre>
                  </div>
                ) : null}
              </div>
            ),
            okText: "关闭",
            width: 600,
          });
        }
      },
    });
  }, [currentSession, selectedAgent, chatHistory, saveChatHistory]);

  // 导出聊天记录
  const handleExportChat = useCallback(() => {
    if (!currentSession || messages.length === 0) {
      return;
    }

    const exportData = {
      agent_name: currentSession.agent_name,
      created_at: currentSession.created_at,
      messages: messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp,
      })),
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chat_${currentSession.agent_name}_${getCurrentUtcTime("YYYY-MM-DD")}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [currentSession, messages]);

  // 键盘事件处理
  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    },
    [handleSendMessage],
  );

  // 重新发送消息
  const handleResendMessage = useCallback(
    async (msg: ChatMessage) => {
      // 检查是否是历史消息（具有真正的数据库ID）
      if (
        !msg.remoteId ||
        !selectedAgent?.id ||
        resending === msg.id ||
        msg.remoteId.startsWith("user_") ||
        msg.remoteId.startsWith("assistant_") ||
        msg.remoteId.startsWith("error_")
      ) {
        message.warning("只能重新发送历史消息");
        return;
      }

      setResending(msg.id);

      try {
        // 调用清理消息接口，删除包含该消息在内的后续对话记录
        const clearResult = await api.chat.clearMessages(
          selectedAgent.id,
          msg.remoteId,
        );

        if (clearResult) {
          message.success(`已删除相关消息记录`);

          // 从本地状态中移除被删除的消息（从该消息开始的所有后续消息）
          setMessages((prev) => {
            const targetIndex = prev.findIndex((m) => m.id === msg.id);
            if (targetIndex !== -1) {
              return prev.slice(0, targetIndex);
            }
            return prev;
          });

          // 重新发送该条消息
          const userMessage: ChatMessage = {
            id: `msg_${Date.now()}`,
            role: "user",
            content: msg.content,
            timestamp: new Date().toISOString(),
          };

          // 添加用户消息
          setMessages((prev) => [...prev, userMessage]);
          setSending(true);

          try {
            // 构造OpenAI格式的消息历史
            const messageHistory = [
              ...messages.slice(
                0,
                messages.findIndex((m) => m.id === msg.id),
              ),
              { role: "user" as const, content: msg.content },
            ];

            // 调用聊天API重新发送
            const response = await api.chat.sendMessage(
              selectedAgent.id,
              messageHistory,
              false,
              { localId: userMessage.id },
            );

            const assistantContent =
              response.choices[0]?.message?.content || "抱歉，我现在无法回复。";

            const assistantMessage: ChatMessage = {
              id: `msg_${Date.now() + 1}`,
              role: "assistant",
              content: assistantContent,
              timestamp: new Date().toISOString(),
            };

            setMessages((prev) => [...prev, assistantMessage]);
          } catch (sendError) {
            console.error("重新发送消息失败:", sendError);
            message.error("重新发送消息失败，请重试");
          } finally {
            setSending(false);
          }
        } else {
          throw new Error("清理消息失败");
        }
      } catch (error) {
        console.error("重新发送失败:", error);
        message.error("重新发送失败，请重试");
      } finally {
        setResending(null);
      }
    },
    [selectedAgent?.id, resending, messages],
  );

  // 删除消息
  const handleDeleteMessage = useCallback(
    async (msg: ChatMessage) => {
      // 检查是否是历史消息（具有真正的数据库ID）
      if (
        !msg.remoteId ||
        !selectedAgent?.id ||
        clearing === msg.id ||
        msg.remoteId.startsWith("user_") ||
        msg.remoteId.startsWith("assistant_") ||
        msg.remoteId.startsWith("error_")
      ) {
        message.warning("只能删除历史消息");
        return;
      }

      setClearing(msg.id);

      try {
        // 调用清理消息接口，删除包含该消息在内的后续对话记录
        const clearResult = await api.chat.clearMessages(
          selectedAgent.id,
          msg.remoteId,
        );

        if (clearResult) {
          message.success(`已删除相关消息记录`);

          // 从本地状态中移除被删除的消息（从该消息开始的所有后续消息）
          setMessages((prev) => {
            const targetIndex = prev.findIndex((m) => m.id === msg.id);
            if (targetIndex !== -1) {
              return prev.slice(0, targetIndex);
            }
            return prev;
          });
        } else {
          throw new Error("清理消息失败");
        }
      } catch (error) {
        console.error("删除消息失败:", error);
        message.error("删除消息失败，请重试");
      } finally {
        setClearing(null);
      }
    },
    [selectedAgent?.id, clearing],
  );

  // 处理括号内容的样式 - 复刻inty-test的formatMessageContent功能
  const formatMessageContent = (content: string) => {
    // 匹配中文括号和英文括号内的内容
    const regex = /([（(].*?[）)])/g;

    const parts = content.split(regex);

    return parts.map((part, index) => {
      if (regex.test(part)) {
        // 括号内容，使用淡色斜体
        return (
          <span
            key={index}
            style={{
              color: "#666",
              fontStyle: "italic",
              opacity: 0.85,
            }}
          >
            {part}
          </span>
        );
      }
      return part;
    });
  };

  return (
    <Layout
      className="chat-page"
      style={{ height: "100vh", overflow: "hidden" }}
    >
      <Content
        style={{
          padding: "24px",
          background: "#f0f2f5",
          height: "100%",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Row gutter={24} style={{ flex: 1, minHeight: 0 }}>
          {/* 智能体选择侧栏 */}
          <Col span={6} style={{ height: "100%" }}>
            <SingleAgentSelectorPanel
              selectedAgentId={selectedAgent?.id}
              onSelectAgent={handleSelectAgent}
            />
          </Col>

          {/* 聊天区域 */}
          <Col span={18} style={{ height: "100%" }}>
            {selectedAgent ? (
              <Card
                title={
                  <Space>
                    <Tooltip title="查看角色详情">
                      <Button
                        type="text"
                        onClick={() => setAgentDetailModalVisible(true)}
                        style={{
                          width: 40,
                          height: 40,
                          padding: 0,
                          borderRadius: "50%",
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <AvatarDisplay agent={selectedAgent} size={32} />
                      </Button>
                    </Tooltip>
                    <div>
                      <Text strong>{selectedAgent.name}</Text>
                      <Text
                        type="secondary"
                        style={{
                          fontSize: "12px",
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          display: "block",
                        }}
                      >
                        ID: {selectedAgent.id}
                      </Text>
                      <Text
                        type="secondary"
                        style={{
                          fontSize: "12px",
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          display: "block",
                        }}
                      >
                        INTRO: {selectedAgent.intro}
                      </Text>
                    </div>
                  </Space>
                }
                extra={
                  <Space>
                    <ChatModeSelector agentId={selectedAgent.id} />
                    <PremiumModeToggle
                      agentId={selectedAgent.id}
                      onToggle={(enabled) => {
                        console.log("Premium mode toggled:", enabled);
                        // Premium mode has been successfully updated via API
                        // The component handles the API call internally
                      }}
                    />
                    <Tooltip title="打开 LangSmith 监控">
                      <Button
                        icon={
                          <img
                            src="/evaluation/resources/langsmith.png"
                            alt="LangSmith"
                            style={{
                              width: "38px",
                              height: "18px",
                              objectFit: "contain",
                            }}
                          />
                        }
                        onClick={() => {
                          window.open(
                            "https://smith.langchain.com/o/e91da43a-00f9-4d3e-a615-413bcf3ba1ac/projects/p/4b428bee-1b11-4e87-b87f-ace2c5aa162a",
                            "_blank",
                          );
                        }}
                        style={{
                          width: "50px",
                          padding: "3px 4px 0px 4px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      />
                    </Tooltip>

                    <Tooltip title="查看聊天历史">
                      <Button
                        icon={<HistoryOutlined />}
                        onClick={handleShowChatHistory}
                        loading={historyLoading}
                      />
                    </Tooltip>
                    <Tooltip title="导出聊天记录">
                      <Button
                        icon={<DownloadOutlined />}
                        onClick={handleExportChat}
                        disabled={messages.length === 0}
                      />
                    </Tooltip>
                    <Tooltip title="清空聊天记录">
                      <Button
                        icon={<ClearOutlined />}
                        onClick={handleClearChat}
                        disabled={messages.length === 0}
                      />
                    </Tooltip>
                  </Space>
                }
                style={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                }}
                bodyStyle={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  padding: 0,
                  overflow: "hidden",
                }}
              >
                {/* 消息列表 */}
                <div
                  style={{
                    flex: 1,
                    minHeight: 0,
                    position: "relative",
                    display: "flex",
                    flexDirection: "column",
                    backgroundColor: "#0f111a",
                    borderBottomLeftRadius: 8,
                    borderBottomRightRadius: 8,
                    overflow: "hidden",
                  }}
                >
                  {(backgroundImageUrl || backgroundAnimatedUrl) && (
                    <div
                      aria-hidden
                      style={{
                        position: "absolute",
                        inset: 0,
                        overflow: "hidden",
                        pointerEvents: "none",
                        zIndex: 0,
                      }}
                    >
                      {backgroundImageUrl && (
                        <img
                          src={backgroundImageUrl}
                          alt={`${backgroundAltName} background`}
                          style={{
                            position: "absolute",
                            inset: 0,
                            width: "100%",
                            height: "100%",
                            objectFit: "cover",
                            filter: backgroundAnimatedUrl
                              ? "blur(6px)"
                              : "none",
                            transform: "scale(1.05)",
                            opacity: backgroundAnimatedUrl ? 0.4 : 0.85,
                            transition: "opacity 0.3s ease",
                          }}
                        />
                      )}
                      {backgroundAnimatedUrl && (
                        <img
                          key={backgroundAnimatedUrl}
                          src={backgroundAnimatedUrl}
                          alt={`${backgroundAltName} animated background`}
                          style={{
                            position: "absolute",
                            inset: 0,
                            width: "100%",
                            height: "100%",
                            objectFit: "cover",
                            opacity: 0.95,
                            filter: "saturate(1.05)",
                            transition: "opacity 0.3s ease",
                          }}
                          onError={(event) => {
                            event.currentTarget.style.display = "none";
                          }}
                        />
                      )}
                      <div
                        style={{
                          position: "absolute",
                          inset: 0,
                          background:
                            "linear-gradient(180deg, rgba(12,14,25,0.25) 0%, rgba(12,14,25,0.85) 100%)",
                        }}
                      />
                    </div>
                  )}
                  <div
                    style={{
                      position: "relative",
                      zIndex: 1,
                      flex: 1,
                      overflowY: "auto",
                      padding: "16px",
                    }}
                  >
                    {/* 角色介绍卡片 - 只在聊天开始时显示 */}
                    {selectedAgent?.intro && messages.length === 0 && (
                      <Card
                        size="small"
                        style={{
                          marginBottom: "16px",
                          backgroundColor: "rgba(255, 255, 255, 0.95)",
                          border: "1px solid #e8f4fd",
                          borderRadius: "12px",
                          boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
                        }}
                        bodyStyle={{
                          padding: "16px",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "flex-start",
                            gap: "12px",
                          }}
                        >
                          <AvatarDisplay agent={selectedAgent!} size={40} />
                          <div style={{ flex: 1 }}>
                            <Text
                              strong
                              style={{ fontSize: "16px", color: "#1890ff" }}
                            >
                              {selectedAgent.name}
                            </Text>
                            <div style={{ marginTop: "8px" }}>
                              <Text
                                style={{
                                  fontSize: "14px",
                                  lineHeight: "1.6",
                                  color: "#666",
                                  whiteSpace: "pre-wrap",
                                  wordBreak: "break-word",
                                  display: "block",
                                }}
                              >
                                {selectedAgent.intro}
                              </Text>
                            </div>
                          </div>
                        </div>
                      </Card>
                    )}

                    {messages.length > 0 && (
                      <List
                        dataSource={messages}
                        rowKey={(msg: ChatMessage) => msg.remoteId ?? msg.id}
                        renderItem={(message: ChatMessage, index: number) => (
                          <div>
                            <List.Item
                              style={{
                                border: "none",
                                padding: "8px 0",
                                justifyContent:
                                  message.role === "user"
                                    ? "flex-end"
                                    : "flex-start",
                              }}
                            >
                              <div
                                style={{
                                  maxWidth: "70%",
                                  display: "flex",
                                  flexDirection:
                                    message.role === "user"
                                      ? "row-reverse"
                                      : "row",
                                  alignItems: "flex-start",
                                  gap: "8px",
                                }}
                              >
                                {message.role === "user" ? (
                                  <Avatar
                                    size="small"
                                    icon={<UserOutlined />}
                                    style={{
                                      backgroundColor: "#1890ff",
                                      flexShrink: 0,
                                    }}
                                  />
                                ) : (
                                  <AvatarDisplay
                                    agent={selectedAgent}
                                    size={24}
                                    style={{
                                      flexShrink: 0,
                                    }}
                                  />
                                )}
                                <div
                                  style={{
                                    backgroundColor:
                                      message.role === "user"
                                        ? "rgba(24, 144, 255, 0.8)"
                                        : "rgba(255, 255, 255, 0.8)",
                                    color:
                                      message.role === "user" ? "#fff" : "#000",
                                    padding: "12px 16px",
                                    borderRadius: "18px",
                                    boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
                                    position: "relative",
                                    border:
                                      message.role === "assistant"
                                        ? "1px solid #f0f0f0"
                                        : "none",
                                  }}
                                >
                                  {isSurpriseSnapMessage(message) ? (
                                    <div style={{ marginTop: 0 }}>
                                      <div style={{ marginBottom: 6 }}>
                                        <Tag color="purple">Fun Moment</Tag>
                                      </div>
                                      {!message.is_locked ||
                                      subscriptionStatus?.is_subscribed ||
                                      userProfile?.is_superuser ? (
                                        <>
                                          {message.media_url && (
                                            <Image
                                              src={message.media_url}
                                              alt="Surprise Snap"
                                              style={{
                                                maxWidth: "300px",
                                                borderRadius: "8px",
                                              }}
                                              placeholder={
                                                <Spin size="small" />
                                              }
                                            />
                                          )}
                                          {message.caption && (
                                            <div style={{ marginTop: 8 }}>
                                              {message.caption}
                                            </div>
                                          )}
                                        </>
                                      ) : (
                                        <>
                                          <div
                                            style={{
                                              position: "relative",
                                              display: "inline-block",
                                            }}
                                          >
                                            {message.media_url && (
                                              <Image
                                                src={message.media_url}
                                                alt=""
                                                style={{
                                                  maxWidth: 300,
                                                  borderRadius: 8,
                                                  filter: "blur(12px)",
                                                  pointerEvents: "none",
                                                }}
                                              />
                                            )}
                                            <div
                                              style={{
                                                position: "absolute",
                                                top: "50%",
                                                left: "50%",
                                                transform:
                                                  "translate(-50%,-50%)",
                                                fontSize: 32,
                                                color: "#722ed1",
                                              }}
                                            >
                                              <CrownOutlined />
                                            </div>
                                          </div>
                                          {message.caption && (
                                            <div style={{ marginTop: 8 }}>
                                              {message.caption}
                                            </div>
                                          )}
                                          <Button
                                            type="primary"
                                            size="small"
                                            loading={
                                              unlockingSurpriseSnapId ===
                                              Number(message.remoteId)
                                            }
                                            onClick={() =>
                                              message.remoteId &&
                                              handleSurpriseSnapUnlock(
                                                Number(message.remoteId),
                                              )
                                            }
                                            style={{ marginTop: 8 }}
                                          >
                                            用 Credits 解锁（
                                            {message.price ?? 0}）
                                          </Button>
                                        </>
                                      )}
                                    </div>
                                  ) : (
                                    <>
                                      {/* 显示文本消息 */}
                                      <Paragraph
                                        style={{
                                          margin: 0,
                                          color:
                                            message.role === "user"
                                              ? "#fff"
                                              : "#000",
                                          whiteSpace: "pre-wrap",
                                          wordBreak: "break-word",
                                        }}
                                      >
                                        {message.type ===
                                        "festival_memory_prompt" ? (
                                          <>
                                            {(message.content || "")
                                              .replace(
                                                /\{char\}/g,
                                                selectedAgent?.name ?? "角色",
                                              )
                                              .replace("静静查看", "")
                                              .trim()}{" "}
                                            <a
                                              onClick={() =>
                                                setFestivalMemoryModalOpen(true)
                                              }
                                              style={{
                                                color: "#722ed1",
                                                textDecoration: "underline",
                                                cursor: "pointer",
                                              }}
                                            >
                                              静静查看
                                            </a>
                                          </>
                                        ) : message.content &&
                                          message.role === "assistant" ? (
                                          formatMessageContent(message.content)
                                        ) : (
                                          message.content || ""
                                        )}
                                      </Paragraph>

                                      {/* 如果有生成的图片，在文本下方显示 */}
                                      {message.role === "assistant" &&
                                        message.meta_data?.generated_image && (
                                          <div style={{ marginTop: "12px" }}>
                                            <Image
                                              src={
                                                message.meta_data
                                                  .generated_image.image_url
                                              }
                                              alt="Generated image"
                                              style={{
                                                maxWidth: "300px",
                                                borderRadius: "8px",
                                              }}
                                              placeholder={
                                                <Spin size="small" />
                                              }
                                            />
                                            {/* 匹配图片标识 */}
                                            {message.meta_data.generated_image
                                              .is_matched && (
                                              <div style={{ marginTop: "6px" }}>
                                                <Tooltip
                                                  title={`相似度: ${Math.round((message.meta_data.generated_image.similarity || 0) * 100)}%`}
                                                >
                                                  <Tag color="orange">
                                                    匹配图片
                                                  </Tag>
                                                </Tooltip>
                                              </div>
                                            )}
                                            {/* 非匹配图片：显示生图耗时和模型 */}
                                            {!message.meta_data.generated_image
                                              .is_matched &&
                                              (message.meta_data.generated_image
                                                .model ||
                                                message.meta_data
                                                  .generated_image
                                                  .generation_time_ms) && (
                                                <div
                                                  style={{
                                                    marginTop: "6px",
                                                    fontSize: "11px",
                                                    color: "#888",
                                                  }}
                                                >
                                                  {message.meta_data
                                                    .generated_image.model && (
                                                    <span>
                                                      模型:{" "}
                                                      {
                                                        message.meta_data
                                                          .generated_image.model
                                                      }
                                                    </span>
                                                  )}
                                                  {message.meta_data
                                                    .generated_image.model &&
                                                    message.meta_data
                                                      .generated_image
                                                      .generation_time_ms && (
                                                      <span> | </span>
                                                    )}
                                                  {message.meta_data
                                                    .generated_image
                                                    .generation_time_ms && (
                                                    <span>
                                                      耗时:{" "}
                                                      {(
                                                        message.meta_data
                                                          .generated_image
                                                          .generation_time_ms /
                                                        1000
                                                      ).toFixed(1)}
                                                      s
                                                    </span>
                                                  )}
                                                </div>
                                              )}
                                          </div>
                                        )}
                                    </>
                                  )}
                                  <div
                                    style={{
                                      fontSize: "10px",
                                      opacity: 0.7,
                                      marginTop: "4px",
                                      textAlign:
                                        message.role === "user"
                                          ? "right"
                                          : "left",
                                      display: "flex",
                                      justifyContent: "space-between",
                                      alignItems: "center",
                                    }}
                                  >
                                    <span>
                                      <ClockCircleOutlined
                                        style={{ marginRight: "2px" }}
                                      />
                                      {formatUtcTimeOnly(message.timestamp)}
                                    </span>
                                    <div
                                      className="message-actions"
                                      style={{
                                        opacity: 1,
                                        display: "flex",
                                        gap: "4px",
                                        alignItems: "center",
                                      }}
                                    >
                                      {/* 语音播放按钮 - 只对AI回复且有真实消息ID的消息显示（排除节日记忆提示、Surprise Snap） */}
                                      {message.role === "assistant" &&
                                        message.type !==
                                          "festival_memory_prompt" &&
                                        !isSurpriseSnapMessage(message) &&
                                        message.remoteId &&
                                        !message.remoteId.startsWith(
                                          "assistant_",
                                        ) &&
                                        !message.remoteId.startsWith(
                                          "error_",
                                        ) &&
                                        !message.remoteId.startsWith(
                                          "remote_",
                                        ) &&
                                        selectedAgent && (
                                          <VoicePlayer
                                            agentId={selectedAgent.id}
                                            messageId={message.remoteId}
                                            messageText={message.content}
                                            language="zh"
                                            size="small"
                                            style={{
                                              color: "#666",
                                              padding: "2px 4px",
                                              height: "auto",
                                              minWidth: "auto",
                                            }}
                                          />
                                        )}

                                      {/* 图片生成按钮 - 只在最后一条AI文本消息显示（排除节日记忆提示） */}
                                      {message.role === "assistant" &&
                                        message.type !== "image" &&
                                        !isSurpriseSnapMessage(message) &&
                                        message.type !==
                                          "festival_memory_prompt" &&
                                        message.remoteId &&
                                        typeof message.remoteId === "string" &&
                                        !message.remoteId.startsWith(
                                          "assistant_",
                                        ) &&
                                        !message.remoteId.startsWith(
                                          "error_",
                                        ) &&
                                        !message.remoteId.startsWith(
                                          "remote_",
                                        ) &&
                                        !isNaN(Number(message.remoteId)) &&
                                        selectedAgent &&
                                        selectedAgent.id &&
                                        index ===
                                          getLastAssistantMessageIndex() && (
                                          <MessageToImageIcon
                                            messageId={Number(message.remoteId)}
                                            agentId={selectedAgent.id}
                                            hasImage={
                                              !!message.meta_data
                                                ?.generated_image
                                            }
                                            size="small"
                                            onImageGenerated={(imageData) => {
                                              // 立即更新当前消息的 meta_data，提供即时反馈
                                              setMessages((prevMessages) => {
                                                return prevMessages.map(
                                                  (msg) => {
                                                    if (
                                                      msg.remoteId ===
                                                      message.remoteId
                                                    ) {
                                                      return {
                                                        ...msg,
                                                        meta_data: {
                                                          ...msg.meta_data,
                                                          generated_image: {
                                                            image_url:
                                                              imageData.image_url,
                                                            width:
                                                              imageData.width,
                                                            height:
                                                              imageData.height,
                                                            is_matched:
                                                              imageData.is_matched,
                                                            similarity:
                                                              imageData.similarity,
                                                            model:
                                                              imageData.model,
                                                            generation_time_ms:
                                                              imageData.generation_time_ms,
                                                          },
                                                        },
                                                      };
                                                    }
                                                    return msg;
                                                  },
                                                );
                                              });
                                              // 图片已立即显示，无需刷新
                                              // 用户刷新页面时会从服务器同步最新数据
                                            }}
                                          />
                                        )}

                                      {/* 点赞/点踩按钮 - 仅对 AI 消息显示（排除节日记忆提示、Surprise Snap） */}
                                      {message.role === "assistant" &&
                                        message.type !==
                                          "festival_memory_prompt" &&
                                        !isSurpriseSnapMessage(message) &&
                                        message.remoteId &&
                                        !message.remoteId.startsWith(
                                          "assistant_",
                                        ) &&
                                        !message.remoteId.startsWith(
                                          "error_",
                                        ) &&
                                        !message.remoteId.startsWith(
                                          "remote_",
                                        ) && (
                                          <>
                                            <Tooltip title="点赞">
                                              <Button
                                                type="text"
                                                size="small"
                                                icon={<LikeOutlined />}
                                                onClick={() =>
                                                  handleMessageVote(
                                                    message,
                                                    "like",
                                                  )
                                                }
                                                style={{
                                                  color:
                                                    message.user_vote === "like"
                                                      ? "#1890ff"
                                                      : "#666",
                                                  padding: "2px 4px",
                                                  height: "auto",
                                                  minWidth: "auto",
                                                }}
                                              />
                                            </Tooltip>
                                            <Tooltip title="点踩">
                                              <Button
                                                type="text"
                                                size="small"
                                                icon={<DislikeOutlined />}
                                                onClick={() =>
                                                  handleMessageVote(
                                                    message,
                                                    "dislike",
                                                  )
                                                }
                                                style={{
                                                  color:
                                                    message.user_vote ===
                                                    "dislike"
                                                      ? "#ff4d4f"
                                                      : "#666",
                                                  padding: "2px 4px",
                                                  height: "auto",
                                                  minWidth: "auto",
                                                }}
                                              />
                                            </Tooltip>
                                          </>
                                        )}

                                      {/* 只有历史消息才显示重新发送和删除按钮 */}
                                      {message.remoteId &&
                                        !message.remoteId.startsWith("user_") &&
                                        !message.remoteId.startsWith(
                                          "assistant_",
                                        ) &&
                                        !message.remoteId.startsWith(
                                          "error_",
                                        ) && (
                                          <>
                                            {message.role === "user" && (
                                              <Tooltip title="重新发送">
                                                <Button
                                                  type="text"
                                                  size="small"
                                                  icon={<RedoOutlined />}
                                                  style={{
                                                    color:
                                                      message.role === "user"
                                                        ? "#fff"
                                                        : "#666",
                                                    padding: "2px 4px",
                                                    height: "auto",
                                                    minWidth: "auto",
                                                  }}
                                                  onClick={() =>
                                                    handleResendMessage(message)
                                                  }
                                                />
                                              </Tooltip>
                                            )}
                                            <Tooltip title="删除消息">
                                              <Button
                                                type="text"
                                                size="small"
                                                icon={<DeleteOutlined />}
                                                style={{
                                                  color:
                                                    message.role === "user"
                                                      ? "#fff"
                                                      : "#666",
                                                  padding: "2px 4px",
                                                  height: "auto",
                                                  minWidth: "auto",
                                                }}
                                                onClick={() =>
                                                  handleDeleteMessage(message)
                                                }
                                              />
                                            </Tooltip>
                                          </>
                                        )}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </List.Item>

                            {/* 显示该消息生成的图片 */}
                            {generatedImages.get(message.content) && (
                              <div
                                style={{
                                  display: "flex",
                                  justifyContent: "center",
                                  margin: "8px 0",
                                  padding: "0 16px",
                                }}
                              >
                                <div
                                  style={{
                                    maxWidth: "400px",
                                    borderRadius: "8px",
                                    overflow: "hidden",
                                    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
                                  }}
                                >
                                  <Image
                                    src={generatedImages.get(message.content)!}
                                    alt="Generated image"
                                    style={{
                                      width: "100%",
                                      height: "auto",
                                      display: "block",
                                    }}
                                    placeholder={
                                      <div
                                        style={{
                                          textAlign: "center",
                                          padding: "40px",
                                          backgroundColor: "#f5f5f5",
                                          borderRadius: "8px",
                                        }}
                                      >
                                        <Spin size="large" />
                                      </div>
                                    }
                                  />
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      />
                    )}

                    <div ref={messagesEndRef} />
                  </div>
                </div>

                {/* 输入区域 */}
                <div
                  style={{
                    padding: "16px",
                    backgroundColor: "#fff",
                    borderTop: "1px solid #f0f0f0",
                    flexShrink: 0,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      gap: "8px",
                      alignItems: "flex-end",
                    }}
                  >
                    <TextArea
                      ref={inputRef}
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="输入消息... (Shift+Enter换行，Enter发送)"
                      autoSize={{ minRows: 1, maxRows: 4 }}
                      style={{ flex: 1 }}
                      disabled={sending}
                    />
                    <Button
                      type="primary"
                      icon={<SendOutlined />}
                      onClick={handleSendMessage}
                      loading={sending}
                      disabled={!inputValue.trim()}
                    >
                      发送
                    </Button>
                  </div>

                  {sending && (
                    <div style={{ marginTop: "8px", textAlign: "center" }}>
                      <Spin size="small" />
                      <Text type="secondary" style={{ marginLeft: "8px" }}>
                        {selectedAgent.name} 正在思考中...
                      </Text>
                    </div>
                  )}
                </div>
              </Card>
            ) : (
              <Card style={{ height: "100%" }}>
                <div style={{ textAlign: "center", padding: "100px 0" }}>
                  <Empty
                    description="请选择一个智能体开始聊天"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                </div>
              </Card>
            )}
          </Col>
        </Row>

        <AgentDetailModal
          open={agentDetailModalVisible}
          agent={selectedAgent}
          onClose={() => setAgentDetailModalVisible(false)}
        />

        {/* 聊天历史模态框 */}
        <Modal
          title={
            <Space>
              <HistoryOutlined />
              聊天历史记录
            </Space>
          }
          open={showHistory}
          onCancel={() => setShowHistory(false)}
          footer={null}
          width={1000}
        >
          {messages.length === 0 ? (
            <Empty
              description="暂无聊天记录"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <div>
              <div style={{ marginBottom: 16 }}>
                <Text strong>当前智能体: {selectedAgent?.name}</Text>
                <br />
                <Text type="secondary">
                  共{" "}
                  {
                    messages.filter((m) => m.type !== "festival_memory_prompt")
                      .length
                  }{" "}
                  条消息
                </Text>
              </div>

              {/* 消息列表 */}
              <List
                dataSource={messages}
                renderItem={(message) => (
                  <List.Item key={message.id}>
                    <List.Item.Meta
                      avatar={
                        message.role === "user" ? (
                          <Avatar
                            icon={<UserOutlined />}
                            style={{
                              backgroundColor: "#1890ff",
                            }}
                          />
                        ) : (
                          <AvatarDisplay agent={selectedAgent!} size={32} />
                        )
                      }
                      title={
                        <Space>
                          <Text strong>
                            {message.role === "user" ? "用户" : "AI助手"}
                          </Text>
                          <Text type="secondary" style={{ fontSize: "12px" }}>
                            {formatUtcTimeRaw(message.timestamp)}
                          </Text>
                        </Space>
                      }
                      description={
                        <div>
                          <div
                            style={{
                              whiteSpace: "pre-wrap",
                              wordBreak: "break-word",
                              maxHeight: "200px",
                              overflowY: "auto",
                            }}
                          >
                            {message.content}
                          </div>
                          {/* 仅对 AI 消息显示点赞/点踩按钮 */}
                          {message.role === "assistant" && (
                            <div
                              style={{
                                marginTop: 8,
                                display: "flex",
                                gap: 8,
                                alignItems: "center",
                              }}
                            >
                              <Button
                                type="text"
                                size="small"
                                icon={<LikeOutlined />}
                                onClick={() =>
                                  handleMessageVote(message, "like")
                                }
                                style={{
                                  color:
                                    message.user_vote === "like"
                                      ? "#1890ff"
                                      : undefined,
                                }}
                              >
                                点赞
                              </Button>
                              <Button
                                type="text"
                                size="small"
                                icon={<DislikeOutlined />}
                                onClick={() =>
                                  handleMessageVote(message, "dislike")
                                }
                                style={{
                                  color:
                                    message.user_vote === "dislike"
                                      ? "#ff4d4f"
                                      : undefined,
                                }}
                              >
                                点踩
                              </Button>
                            </div>
                          )}
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />

              {/* 原始JSON数据显示 */}
              <div
                style={{
                  marginTop: 24,
                  paddingTop: 16,
                  borderTop: "1px solid #f0f0f0",
                }}
              >
                <h4
                  style={{
                    margin: "8px 0",
                    fontSize: "14px",
                    fontWeight: "bold",
                    color: "#666",
                  }}
                >
                  原始JSON数据
                </h4>
                <div
                  style={{
                    background: "#f5f5f5",
                    padding: "12px",
                    borderRadius: "6px",
                    fontSize: "11px",
                    lineHeight: "1.4",
                    fontFamily: "monospace",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    border: "1px solid #e0e0e0",
                    maxHeight: "300px",
                    overflowY: "auto",
                  }}
                >
                  {JSON.stringify(messages, null, 2)}
                </div>
              </div>
            </div>
          )}
        </Modal>

        {/* 心跳日记弹窗：通过 agent info 接口返回的 features.festival_memories 展示节日记忆 */}
        <Modal
          title="心跳日记"
          open={festivalMemoryModalOpen}
          onCancel={() => setFestivalMemoryModalOpen(false)}
          footer={null}
          width={640}
          destroyOnClose
        >
          {festivalMemoriesLoading ? (
            <div style={{ textAlign: "center", padding: "24px 0" }}>
              <Spin />
            </div>
          ) : (
            <div style={{ maxHeight: "60vh", overflowY: "auto" }}>
              {agentWithFestivalMemories?.features?.festival_memories &&
              agentWithFestivalMemories.features.festival_memories.length >
                0 ? (
                <Row gutter={[12, 12]}>
                  {(
                    agentWithFestivalMemories.features
                      .festival_memories as FestivalMemoryItem[]
                  ).map((item, idx) => (
                    <Col span={12} key={`${item.festival_date}-${idx}`}>
                      <Card
                        size="small"
                        title={
                          item.festival_name || item.festival_date || "节日记忆"
                        }
                        style={{ height: "100%" }}
                      >
                        <Text
                          style={{
                            fontSize: "13px",
                            lineHeight: 1.6,
                            color: "#333",
                          }}
                        >
                          {item.memory}
                        </Text>
                      </Card>
                    </Col>
                  ))}
                </Row>
              ) : (
                <Empty description="暂无节日记忆" />
              )}
            </div>
          )}
        </Modal>

        <Modal
          title="图片反馈表单"
          open={imageFeedbackFormVisible}
          onCancel={() => {
            if (submittingImageFeedback) {
              return;
            }
            setImageFeedbackFormVisible(false);
            setPendingImageFeedback(null);
            setImageFeedbackText("");
          }}
          onOk={handleSubmitImageFeedback}
          okText="提交反馈"
          cancelText="取消"
          confirmLoading={submittingImageFeedback}
        >
          {pendingImageFeedback && (
            <Space direction="vertical" style={{ width: "100%" }} size={12}>
              <div style={{ color: "#666", fontSize: 13 }}>
                已自动记录图片 URL，你可以补充文字反馈。
              </div>
              <Image
                src={pendingImageFeedback.imageUrl}
                alt="反馈图片"
                style={{ maxWidth: 280, borderRadius: 8 }}
              />
              <Input value={pendingImageFeedback.imageUrl} readOnly />
              <Tag
                color={pendingImageFeedback.vote === "like" ? "green" : "red"}
              >
                {pendingImageFeedback.vote === "like" ? "点赞反馈" : "点踩反馈"}
              </Tag>
              <TextArea
                value={imageFeedbackText}
                onChange={(event) => setImageFeedbackText(event.target.value)}
                placeholder="请补充你对这张图的看法（可选）"
                autoSize={{ minRows: 3, maxRows: 6 }}
                maxLength={500}
              />
            </Space>
          )}
        </Modal>
      </Content>
    </Layout>
  );
};
