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
  Alert,
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
  RobotOutlined,
  UserOutlined,
  ClearOutlined,
  DownloadOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  HistoryOutlined,
  RedoOutlined,
  DeleteOutlined,
} from "@ant-design/icons";
import { useAgents } from "../hooks/useAgents";
import api from "../services/api";
import type { Agent } from "../types";
import VoicePlayer from "../components/common/VoicePlayer";
import { PremiumModeToggle } from "../components/common/PremiumModeToggle";
import { AvatarDisplay } from "../components/common/AvatarDisplay";
import { MessageToImageIcon } from "../components/MessageToImageIcon";

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
  type?: "text" | "image"; // 消息类型：文本或图片
  image_url?: string; // 图片URL（仅图片消息）
  meta_data?: {
    generated_image?: {
      image_url: string;
      width: number;
      height: number;
      prompt?: string;
    };
  };
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

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 智能体数据
  const {
    agents,
    loading: agentsLoading,
    error: agentsError,
    loadAgents,
  } = useAgents({
    type: "all", // 获取所有角色（包括公开和私有）
    autoLoad: true,
  });

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

  // 处理图片生成 - 使用消息内容作为键，因为消息ID会变化
  const handleImageGenerated = useCallback(
    (messageContent: string, imageUrl: string) => {
      setGeneratedImages((prev) => {
        const newMap = new Map(prev.set(messageContent, imageUrl));
        // 保存到localStorage
        const imagesObj = Object.fromEntries(newMap);
        localStorage.setItem("generatedImages", JSON.stringify(imagesObj));
        return newMap;
      });
    },
    [],
  );

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

  // 刷新当前会话的消息列表
  const refreshMessages = useCallback(async () => {
    if (!selectedAgent?.id) {
      return;
    }

    try {
      const messagesData = await api.chat.getMessages(selectedAgent.id, {
        page: 1,
        size: 100,
      });

      if (messagesData.messages && messagesData.messages.length > 0) {
        const convertedMessages: ChatMessage[] = messagesData.messages.map(
          (msg, index) => ({
            id: `msg_${selectedAgent.id}_${index}_${Date.now()}`,
            role: msg.role,
            content: msg.content || "",
            timestamp: msg.timestamp,
            remoteId: msg.id.toString(),
            type: msg.type || "text",
            image_url: msg.image_url,
            meta_data: msg.meta_data,
          }),
        );

        // 去重：根据 remoteId 去除重复消息
        const uniqueMessages = convertedMessages.filter(
          (msg, index, self) =>
            index === self.findIndex((m) => m.remoteId === msg.remoteId),
        );

        console.log(
          `消息列表已刷新，共 ${convertedMessages.length} 条消息（去重后 ${uniqueMessages.length} 条）`,
        );
        console.log(
          "图片消息数量:",
          uniqueMessages.filter((m) => m.type === "image").length,
        );
        console.log("所有消息:", uniqueMessages);

        setMessages(uniqueMessages);
      }
    } catch (error) {
      console.error("刷新消息列表失败:", error);
    }
  }, [selectedAgent?.id]);

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
            role: msg.role,
            content: msg.content || "",
            timestamp: msg.timestamp,
            remoteId: msg.id.toString(),
            type: msg.type || "text",
            image_url: msg.image_url,
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

  // 选择智能体 - 从后端获取真实会话记录
  const handleSelectAgent = useCallback(
    async (agent: Agent) => {
      setSelectedAgent(agent);
      setSending(true);

      try {
        const currentSettings = await api
          .getIntyClient()
          .api.v1.chats.agents.getSettings(agent.id);
        console.log(`智能体 ${agent.name} 的当前聊天设置:`, currentSettings);
        // 先尝试获取现有的聊天详情和消息历史
        const chatData = await api.chat.getChatDetail(agent.id, {
          page: 1,
          size: 100,
        });

        // 转换消息格式（支持文本和图片消息）
        const convertedMessages: ChatMessage[] = (chatData.messages || []).map(
          (msg, index) => ({
            id: `msg_${chatData.chat_info?.id || "unknown"}_${index}_${Date.now()}`,
            role:
              msg.role || (msg.sender_type === "USER" ? "user" : "assistant"), // 优先使用 role，fallback 到 sender_type
            content: msg.content || "",
            timestamp:
              msg.timestamp || msg.created_at || new Date().toISOString(),
            remoteId: msg.id ? msg.id.toString() : undefined, // 使用真实消息ID
            type: msg.type || "text",
            image_url: msg.image_url,
            meta_data: msg.meta_data,
          }),
        );

        console.log("获取到的聊天数据:", chatData);
        console.log("消息数量:", chatData.messages?.length);
        if (chatData.messages && chatData.messages.length > 0) {
          console.log("第一条消息示例:", chatData.messages[0]);
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

        // 创建会话对象
        const session: ChatSession = {
          id: chatData.chat_info?.id || `temp_${Date.now()}`,
          agent_id: agent.id,
          agent_name: agent.name,
          messages: uniqueMessages,
          created_at:
            chatData.chat_info?.created_at || new Date().toISOString(),
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
                role: msg.role, // 直接使用API返回的role字段（'user' 或 'assistant'）
                content: msg.content || "",
                timestamp: msg.timestamp,
                remoteId: msg.id ? String(msg.id) : `remote_${index}`, // 安全地访问id字段
                type: msg.type || "text",
                image_url: msg.image_url,
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
        // 注意：由于当前的sendMessage API不返回消息ID，暂时使用本地ID
        // 如果需要真正的远程ID，需要调用getChatDetail获取最新的消息
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
              role: msg.role,
              content: msg.content || "",
              timestamp: msg.timestamp,
              remoteId: msg.id ? String(msg.id) : `remote_${index}`,
              type: msg.type || "text",
              image_url: msg.image_url,
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
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
            remoteId: msg.id.toString(), // 添加remoteId
            type: msg.type || "text",
            image_url: msg.image_url,
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
    a.download = `chat_${currentSession.agent_name}_${new Date().toLocaleDateString()}.json`;
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
            <Card
              title={
                <Space>
                  <RobotOutlined />
                  选择智能体
                </Space>
              }
              style={{
                height: "100%",
                display: "flex",
                flexDirection: "column",
              }}
              bodyStyle={{ flex: 1, padding: "16px", overflow: "hidden" }}
              extra={
                <Button
                  icon={<ReloadOutlined />}
                  size="small"
                  onClick={() => loadAgents(true)}
                  loading={agentsLoading}
                />
              }
            >
              {agentsError ? (
                <Alert
                  message="加载失败"
                  description={agentsError}
                  type="error"
                  showIcon
                />
              ) : agents.length === 0 ? (
                <Empty
                  description="暂无可用智能体"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              ) : (
                <div style={{ height: "100%", overflowY: "auto" }}>
                  <List
                    loading={agentsLoading}
                    dataSource={agents}
                    renderItem={(agent) => (
                      <List.Item
                        className={`agent-item ${selectedAgent?.id === agent.id ? "selected" : ""}`}
                        style={{
                          cursor: "pointer",
                          padding: "12px",
                          border:
                            selectedAgent?.id === agent.id
                              ? "2px solid #1890ff"
                              : "1px solid #f0f0f0",
                          borderRadius: "8px",
                          marginBottom: "8px",
                          backgroundColor:
                            selectedAgent?.id === agent.id ? "#f6ffed" : "#fff",
                          transition: "all 0.2s ease",
                        }}
                        onClick={() => handleSelectAgent(agent)}
                      >
                        <List.Item.Meta
                          avatar={<AvatarDisplay agent={agent} size={40} />}
                          title={
                            <Text strong style={{ fontSize: "14px" }}>
                              {agent.name}
                            </Text>
                          }
                          description={
                            <div>
                              <Text
                                type="secondary"
                                style={{
                                  fontSize: "12px",
                                  lineHeight: "1.4",
                                  whiteSpace: "pre-wrap",
                                  wordBreak: "break-word",
                                  display: "block",
                                }}
                              >
                                {agent.intro}
                              </Text>
                              <div style={{ marginTop: 4 }}>
                                {agent.gender && (
                                  <Tag
                                    color={
                                      agent.gender === "MALE"
                                        ? "blue"
                                        : agent.gender === "FEMALE"
                                          ? "pink"
                                          : "default"
                                    }
                                  >
                                    {agent.gender === "MALE"
                                      ? "男"
                                      : agent.gender === "FEMALE"
                                        ? "女"
                                        : "其他"}
                                  </Tag>
                                )}
                                <Tag
                                  color={
                                    agent.visibility === "PUBLIC"
                                      ? "green"
                                      : "orange"
                                  }
                                >
                                  {agent.visibility === "PUBLIC"
                                    ? "公开"
                                    : "私有"}
                                </Tag>
                              </div>
                            </div>
                          }
                        />
                      </List.Item>
                    )}
                  />
                </div>
              )}
            </Card>
          </Col>

          {/* 聊天区域 */}
          <Col span={18} style={{ height: "100%" }}>
            {selectedAgent ? (
              <Card
                title={
                  <Space>
                    <AvatarDisplay agent={selectedAgent} size={32} />
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
                    overflowY: "auto",
                    padding: "16px",
                    backgroundColor: "transparent", // Make background transparent for image
                    minHeight: 0,
                    backgroundImage: selectedAgent?.background
                      ? `url(${selectedAgent.background})`
                      : "none",
                    backgroundSize: "contain",
                    backgroundPosition: "center",
                    backgroundRepeat: "no-repeat",
                    backgroundBlendMode: "multiply", // Blend mode for better visibility
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
                                {/* 显示文本消息 */}
                                <Paragraph
                                  style={{
                                    margin: 0,
                                    color:
                                      message.role === "user" ? "#fff" : "#000",
                                    whiteSpace: "pre-wrap",
                                    wordBreak: "break-word",
                                  }}
                                >
                                  {message.content &&
                                  message.role === "assistant"
                                    ? formatMessageContent(message.content)
                                    : message.content || ""}
                                </Paragraph>

                                {/* 如果有生成的图片，在文本下方显示 */}
                                {message.role === "assistant" &&
                                  message.meta_data?.generated_image && (
                                    <div style={{ marginTop: "12px" }}>
                                      <Image
                                        src={
                                          message.meta_data.generated_image
                                            .image_url
                                        }
                                        alt="Generated image"
                                        style={{
                                          maxWidth: "300px",
                                          borderRadius: "8px",
                                        }}
                                        placeholder={<Spin size="small" />}
                                      />
                                    </div>
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
                                    {new Date(
                                      message.timestamp,
                                    ).toLocaleTimeString()}
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
                                    {/* 语音播放按钮 - 只对AI回复且有真实消息ID的消息显示 */}
                                    {message.role === "assistant" &&
                                      message.remoteId &&
                                      !message.remoteId.startsWith(
                                        "assistant_",
                                      ) &&
                                      !message.remoteId.startsWith("error_") &&
                                      !message.remoteId.startsWith("remote_") &&
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

                                    {/* 图片生成按钮 - 只在最后一条AI文本消息显示 */}
                                    {message.role === "assistant" &&
                                      message.type !== "image" &&
                                      message.remoteId &&
                                      typeof message.remoteId === "string" &&
                                      !message.remoteId.startsWith(
                                        "assistant_",
                                      ) &&
                                      !message.remoteId.startsWith("error_") &&
                                      !message.remoteId.startsWith("remote_") &&
                                      !isNaN(Number(message.remoteId)) &&
                                      selectedAgent &&
                                      selectedAgent.id &&
                                      index ===
                                        getLastAssistantMessageIndex() && (
                                        <MessageToImageIcon
                                          messageId={Number(message.remoteId)}
                                          agentId={selectedAgent.id}
                                          hasImage={
                                            !!message.meta_data?.generated_image
                                          }
                                          size="small"
                                          onImageGenerated={(imageData) => {
                                            // 立即更新当前消息的 meta_data，提供即时反馈
                                            setMessages((prevMessages) => {
                                              return prevMessages.map((msg) => {
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
                                                        width: imageData.width,
                                                        height:
                                                          imageData.height,
                                                      },
                                                    },
                                                  };
                                                }
                                                return msg;
                                              });
                                            });
                                            // 图片已立即显示，无需刷新
                                            // 用户刷新页面时会从服务器同步最新数据
                                          }}
                                        />
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
                <Text type="secondary">共 {messages.length} 条消息</Text>
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
                            {new Date(message.timestamp).toLocaleString()}
                          </Text>
                        </Space>
                      }
                      description={
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
      </Content>
    </Layout>
  );
};
