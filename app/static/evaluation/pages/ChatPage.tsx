/**
 * 单角色聊天页面
 * 提供与单个智能体的实时聊天功能
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Layout,
  Card,
  Input,
  Button,
  List,
  Avatar,
  Space,
  Typography,
  Select,
  Divider,
  Spin,
  Alert,
  Modal,
  Tooltip,
  Tag,
  Row,
  Col,
  Empty,
  message,
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  ClearOutlined,
  DownloadOutlined,
  SettingOutlined,
  MessageOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  HistoryOutlined,
  EyeOutlined,
  TeamOutlined,
  RedoOutlined,
  DeleteOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useAgents } from '../hooks/useAgents';
import api from '../services/api';
import type { Agent, ChatMessage } from '../types';
import VoicePlayer from '../components/common/VoicePlayer';

const { Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface ChatSession {
  id: string;
  agent_id: string;
  agent_name: string;
  messages: ChatMessage[];
  created_at: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant'; // 与API返回的role字段一致，值为 'user' 或 'assistant'
  content: string;
  timestamp: string;
  remoteId?: string;  // 数据库消息ID，用于删除和重发功能
}

export const ChatPage: React.FC = () => {
  // 状态管理
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatSession[]>([]);
  const [isGuestMode, setIsGuestMode] = useState(false);
  const [showPrompt, setShowPrompt] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<any>(null);

  // 智能体数据
  const {
    agents,
    loading: agentsLoading,
    error: agentsError,
    loadAgents,
  } = useAgents({
    type: 'all', // 获取所有角色（包括公开和私有）
    autoLoad: true,
  });

  // 调试消息相关状态
  const [debugModalVisible, setDebugModalVisible] = useState(false);
  const [debugData, setDebugData] = useState<any>(null);
  const [debugLoading, setDebugLoading] = useState(false);

  // 重新发送和删除消息相关状态
  const [resending, setResending] = useState<string | null>(null);
  const [clearing, setClearing] = useState<string | null>(null);

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // 滚动到底部当消息更新时
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // 加载聊天历史
  const loadChatHistory = useCallback(async () => {
    try {
      const history = localStorage.getItem('chat_history');
      if (history) {
        setChatHistory(JSON.parse(history));
      }
    } catch (error) {
      console.error('加载聊天历史失败:', error);
    }
  }, []);

  // 保存聊天历史
  const saveChatHistory = useCallback((sessions: ChatSession[]) => {
    try {
      localStorage.setItem('chat_history', JSON.stringify(sessions));
    } catch (error) {
      console.error('保存聊天历史失败:', error);
    }
  }, []);

  // 初始化加载历史
  useEffect(() => {
    loadChatHistory();
  }, [loadChatHistory]);

  // 选择智能体 - 从后端获取真实会话记录
  const handleSelectAgent = useCallback(async (agent: Agent) => {
    setSelectedAgent(agent);
    setSending(true);

    try {
      // 先尝试获取现有的聊天详情和消息历史
      const chatData = await api.chat.getChatDetail(agent.id, { page: 1, size: 100 });

      // 转换消息格式
      const convertedMessages: ChatMessage[] = chatData.messages.map((msg, index) => ({
        id: `msg_${chatData.chat.id}_${index}_${Date.now()}`,
        role: msg.sender_type === 'USER' ? 'user' : 'assistant',
        content: msg.content,
        timestamp: msg.created_at,
        sender_type: msg.sender_type,
        remoteId: msg.id || `remote_${index}`, // 添加远程消息ID
      }));

      // 创建会话对象
      const session: ChatSession = {
        id: chatData.chat.id,
        agent_id: agent.id,
        agent_name: agent.name,
        messages: convertedMessages,
        created_at: chatData.chat.created_at,
      };

      setCurrentSession(session);
      setMessages(convertedMessages);

      // 更新本地历史记录缓存
      const existingHistoryIndex = chatHistory.findIndex(s => s.agent_id === agent.id);
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

      console.log(`成功加载智能体 ${agent.name} 的聊天记录，共 ${convertedMessages.length} 条消息`);

    } catch (error) {
      console.error('加载聊天会话失败:', error);

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
        const historyData = await api.chat.getMessages(agent.id, { page: 1, size: 100 });
        if (historyData.messages && historyData.messages.length > 0) {
          const convertedMessages: ChatMessage[] = historyData.messages.map((msg, index) => ({
            id: `msg_history_${index}_${Date.now()}`,
            role: msg.role, // 直接使用API返回的role字段（'user' 或 'assistant'）
            content: msg.content,
            timestamp: msg.timestamp,
            remoteId: msg.id ? String(msg.id) : `remote_${index}`, // 安全地访问id字段
          }));

          setMessages(convertedMessages.reverse()); // 反转顺序，最新的在底部
          console.log(`成功加载智能体 ${agent.name} 的历史消息，共 ${convertedMessages.length} 条`);
        }
      } catch (historyError) {
        console.error('加载历史消息失败，继续使用空会话:', historyError);
      }
    } finally {
      setSending(false);
    }
  }, [chatHistory, saveChatHistory]);

  // 发送消息 - 使用现有聊天API
  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || !selectedAgent || !currentSession || sending) {
      return;
    }

    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString(),
      remoteId: `user_${Date.now()}`, // 为用户消息添加临时 remoteId
    };

    // 添加用户消息到UI
    const messagesWithUser = [...messages, userMessage];
    setMessages(messagesWithUser);
    setInputValue('');
    setSending(true);

    try {
      // 构造OpenAI格式的消息历史
      const messageHistory = messagesWithUser.map(msg => ({
        role: msg.role,
        content: msg.content,
      }));

      // 调用现有的OpenAI兼容聊天API
      const response = await api.chat.sendMessage(selectedAgent.id, messageHistory);

      // 添加详细的响应诊断日志
      console.log('=== API响应诊断 ===');
      console.log('完整响应对象:', response);
      console.log('响应类型:', typeof response);
      console.log('响应是否为null:', response === null);
      console.log('响应是否为undefined:', response === undefined);
      console.log('响应是否为数组:', Array.isArray(response));
      console.log('响应键:', response ? Object.keys(response) : 'N/A');

      if (response && typeof response === 'object') {
        console.log('response.choices:', response.choices);
        console.log('response.choices类型:', typeof response.choices);
        console.log('response.choices是否为数组:', Array.isArray(response.choices));
        console.log('response.choices长度:', response.choices?.length);

        if (response.choices && response.choices.length > 0) {
          console.log('response.choices[0]:', response.choices[0]);
          console.log('response.choices[0].message:', response.choices[0]?.message);
          console.log('response.choices[0].message.content:', response.choices[0]?.message?.content);
        }
      }
      console.log('=== 诊断结束 ===');

      // 提取助手回复 - 添加安全检查
      let assistantContent = '抱歉，我现在无法回复。';

      if (response && response.choices && Array.isArray(response.choices) && response.choices.length > 0) {
        const firstChoice = response.choices[0];
        if (firstChoice && firstChoice.message && firstChoice.message.content) {
          assistantContent = firstChoice.message.content;
        } else {
          console.warn('响应结构不完整:', firstChoice);
        }
      } else {
        console.warn('响应中没有找到choices数组或数组为空');
      }

      const assistantMessage: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: 'assistant',
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
        await new Promise(resolve => setTimeout(resolve, 500));

        // 重新获取最新的聊天记录
        const refreshedData = await api.chat.getMessages(selectedAgent.id, { page: 1, size: 100 });

        // 添加刷新数据的诊断日志
        console.log('=== 刷新数据诊断 ===');
        console.log('完整刷新数据:', refreshedData);
        console.log('刷新数据类型:', typeof refreshedData);
        console.log('refreshedData.messages:', refreshedData?.messages);
        console.log('refreshedData.messages类型:', typeof refreshedData?.messages);
        console.log('refreshedData.messages是否为数组:', Array.isArray(refreshedData?.messages));
        console.log('refreshedData.messages长度:', refreshedData?.messages?.length);
        console.log('=== 刷新诊断结束 ===');

        if (refreshedData && refreshedData.messages && Array.isArray(refreshedData.messages) && refreshedData.messages.length > 0) {
          // 添加消息映射诊断
          console.log('=== 消息映射诊断 ===');
          console.log('开始映射消息，总数:', refreshedData.messages.length);

          const refreshedMessages: ChatMessage[] = refreshedData.messages.map((msg, index) => {
            console.log(`映射消息 ${index}:`, msg);
            console.log(`消息 ${index} 的role:`, msg?.role);
            console.log(`消息 ${index} 的content:`, msg?.content);
            console.log(`消息 ${index} 的timestamp:`, msg?.timestamp);
            console.log(`消息 ${index} 的id:`, msg?.id);

            return {
              id: `msg_refreshed_${index}_${Date.now()}`,
              role: msg?.role || 'assistant',
              content: msg?.content || '消息内容为空',
              timestamp: msg?.timestamp || new Date().toISOString(),
              remoteId: msg?.id ? String(msg.id) : `remote_${index}`,
            };
          });

          console.log('映射完成，结果:', refreshedMessages);
          console.log('=== 消息映射诊断结束 ===');

          // 更新消息列表（最新的在底部）
          setMessages(refreshedMessages.reverse());

          // 更新会话
          const updatedSession = {
            ...currentSession,
            messages: refreshedMessages,
          };
          setCurrentSession(updatedSession);

          // 更新历史记录
          const updatedHistory = chatHistory.map(session =>
            session.id === currentSession.id ? updatedSession : session
          );
          setChatHistory(updatedHistory);
          saveChatHistory(updatedHistory);

          console.log('已刷新聊天记录，获取到真实消息ID');
        }
      } catch (refreshError) {
        console.warn('刷新聊天记录失败，但消息发送成功:', refreshError);

        // 如果刷新失败，仍然保留原来的逻辑
        const updatedSession = {
          ...currentSession,
          messages: finalMessages,
        };
        setCurrentSession(updatedSession);

        const updatedHistory = chatHistory.map(session =>
          session.id === currentSession.id ? updatedSession : session
        );
        setChatHistory(updatedHistory);
        saveChatHistory(updatedHistory);
      }

    } catch (error) {
      console.error('发送消息失败:', error);

      // 添加错误消息
      const errorMessage: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: 'assistant',
        content: `发送失败，后端错误信息：${error instanceof Error ? error.message : String(error)}`,
        timestamp: new Date().toISOString(),
        remoteId: `error_${Date.now() + 1}`, // 为错误消息添加 remoteId
      };

      const finalMessages = [...messagesWithUser, errorMessage];
      setMessages(finalMessages);
    } finally {
      setSending(false);
    }
  }, [inputValue, selectedAgent, currentSession, messages, sending, chatHistory, saveChatHistory]);

  // 清空聊天记录 - 使用现有聊天API
  const handleClearChat = useCallback(() => {
    if (!currentSession || !selectedAgent) return;

    Modal.confirm({
      title: '确认清空',
      content: '确定要清空当前聊天记录吗？此操作不可恢复。',
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        try {
          // 调用现有API清除消息
          await api.chat.clearMessages(selectedAgent.id);

          // 更新UI状态
          setMessages([]);

          const updatedSession = {
            ...currentSession,
            messages: [],
          };
          setCurrentSession(updatedSession);

          const updatedHistory = chatHistory.map(session =>
            session.id === currentSession.id ? updatedSession : session
          );
          setChatHistory(updatedHistory);
          saveChatHistory(updatedHistory);

          message.success('聊天记录已清空');
        } catch (error) {
          console.error('清空聊天记录失败:', error);
          message.error('清空聊天记录失败，请重试');
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
      messages: messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp,
      })),
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat_${currentSession.agent_name}_${new Date().toLocaleDateString()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [currentSession, messages]);


  // 键盘事件处理
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  // 获取调试消息
  const fetchDebugMessages = useCallback(async () => {
    if (!selectedAgent?.id) return;

    try {
      setDebugLoading(true);
      const result = await api.chat.getAgentDebugMessages(selectedAgent.id);
      setDebugData(result);
      setDebugModalVisible(true);
    } catch (error) {
      console.error('获取调试消息失败:', error);
      message.error('获取调试消息失败');
    } finally {
      setDebugLoading(false);
    }
  }, [selectedAgent?.id]);

  // 重新发送消息
  const handleResendMessage = useCallback(async (msg: ChatMessage) => {
    // 检查是否是历史消息（具有真正的数据库ID）
    if (!msg.remoteId || !selectedAgent?.id || resending === msg.id ||
      msg.remoteId.startsWith('user_') || msg.remoteId.startsWith('assistant_') || msg.remoteId.startsWith('error_')) {
      message.warning('只能重新发送历史消息');
      return;
    }

    setResending(msg.id);

    try {
      // 调用清理消息接口，删除包含该消息在内的后续对话记录
      const clearResult = await api.chat.clearMessages(selectedAgent.id, msg.remoteId);

      if (clearResult) {
        message.success(`已删除相关消息记录`);

        // 从本地状态中移除被删除的消息（从该消息开始的所有后续消息）
        setMessages(prev => {
          const targetIndex = prev.findIndex(m => m.id === msg.id);
          if (targetIndex !== -1) {
            return prev.slice(0, targetIndex);
          }
          return prev;
        });

        // 重新发送该条消息
        const userMessage: ChatMessage = {
          id: `msg_${Date.now()}`,
          role: 'user',
          content: msg.content,
          timestamp: new Date().toISOString(),
        };

        // 添加用户消息
        setMessages(prev => [...prev, userMessage]);
        setSending(true);

        try {
          // 构造OpenAI格式的消息历史
          const messageHistory = [
            ...messages.slice(0, messages.findIndex(m => m.id === msg.id)),
            { role: 'user' as const, content: msg.content }
          ];

          // 调用聊天API重新发送
          const response = await api.chat.sendMessage(selectedAgent.id, messageHistory);

          const assistantContent = response.choices[0]?.message?.content || '抱歉，我现在无法回复。';

          const assistantMessage: ChatMessage = {
            id: `msg_${Date.now() + 1}`,
            role: 'assistant',
            content: assistantContent,
            timestamp: new Date().toISOString(),
          };

          setMessages(prev => [...prev, assistantMessage]);
        } catch (sendError) {
          console.error('重新发送消息失败:', sendError);
          message.error('重新发送消息失败，请重试');
        } finally {
          setSending(false);
        }
      } else {
        throw new Error('清理消息失败');
      }
    } catch (error) {
      console.error('重新发送失败:', error);
      message.error('重新发送失败，请重试');
    } finally {
      setResending(null);
    }
  }, [selectedAgent?.id, resending, messages]);

  // 删除消息
  const handleDeleteMessage = useCallback(async (msg: ChatMessage) => {
    // 检查是否是历史消息（具有真正的数据库ID）
    if (!msg.remoteId || !selectedAgent?.id || clearing === msg.id ||
      msg.remoteId.startsWith('user_') || msg.remoteId.startsWith('assistant_') || msg.remoteId.startsWith('error_')) {
      message.warning('只能删除历史消息');
      return;
    }

    setClearing(msg.id);

    try {
      // 调用清理消息接口，删除包含该消息在内的后续对话记录
      const clearResult = await api.chat.clearMessages(selectedAgent.id, msg.remoteId);

      if (clearResult) {
        message.success(`已删除相关消息记录`);

        // 从本地状态中移除被删除的消息（从该消息开始的所有后续消息）
        setMessages(prev => {
          const targetIndex = prev.findIndex(m => m.id === msg.id);
          if (targetIndex !== -1) {
            return prev.slice(0, targetIndex);
          }
          return prev;
        });
      } else {
        throw new Error('清理消息失败');
      }
    } catch (error) {
      console.error('删除消息失败:', error);
      message.error('删除消息失败，请重试');
    } finally {
      setClearing(null);
    }
  }, [selectedAgent?.id, clearing]);

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
              color: '#666',
              fontStyle: 'italic',
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
    <Layout className="chat-page" style={{ height: '100vh', overflow: 'hidden' }}>
      <Content style={{ padding: '24px', background: '#f0f2f5', height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Row gutter={24} style={{ flex: 1, minHeight: 0 }}>
          {/* 智能体选择侧栏 */}
          <Col span={6} style={{ height: '100%' }}>
            <Card
              title={
                <Space>
                  <RobotOutlined />
                  选择智能体
                </Space>
              }
              style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
              bodyStyle={{ flex: 1, padding: '16px', overflow: 'hidden' }}
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
                <div style={{ height: '100%', overflowY: 'auto' }}>
                  <List
                    loading={agentsLoading}
                    dataSource={agents}
                    renderItem={(agent) => (
                      <List.Item
                        className={`agent-item ${selectedAgent?.id === agent.id ? 'selected' : ''}`}
                        style={{
                          cursor: 'pointer',
                          padding: '12px',
                          border: selectedAgent?.id === agent.id ? '2px solid #1890ff' : '1px solid #f0f0f0',
                          borderRadius: '8px',
                          marginBottom: '8px',
                          backgroundColor: selectedAgent?.id === agent.id ? '#f6ffed' : '#fff',
                          transition: 'all 0.2s ease',
                        }}
                        onClick={() => handleSelectAgent(agent)}
                      >
                        <List.Item.Meta
                          avatar={
                            <Avatar
                              src={agent.avatar}
                              icon={<RobotOutlined />}
                              style={{
                                backgroundColor: selectedAgent?.id === agent.id ? '#52c41a' : '#1890ff',
                              }}
                            />
                          }
                          title={
                            <Text strong style={{ fontSize: '14px' }}>
                              {agent.name}
                            </Text>
                          }
                          description={
                            <div>
                              <Text type="secondary" style={{ fontSize: '12px', lineHeight: '1.4' }}>
                                {agent.description}
                              </Text>
                              <div style={{ marginTop: 4 }}>
                                {agent.gender && (
                                  <Tag size="small" color={agent.gender === '男' ? 'blue' : agent.gender === '女' ? 'pink' : 'default'}>
                                    {agent.gender}
                                  </Tag>
                                )}
                                <Tag size="small" color={agent.visibility === 'PUBLIC' || agent.visibility === 'public' ? 'green' : 'orange'}>
                                  {agent.visibility === 'PUBLIC' || agent.visibility === 'public' ? '公开' : '私有'}
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
          <Col span={18} style={{ height: '100%' }}>
            {selectedAgent ? (
              <Card
                title={
                  <Space>
                    <Avatar src={selectedAgent.avatar} icon={<RobotOutlined />} />
                    <div>
                      <Text strong>{selectedAgent.name}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {selectedAgent.description}
                      </Text>
                    </div>
                  </Space>
                }
                extra={
                  <Space>
                    <Tooltip title="切换游客模式">
                      <Button
                        icon={<TeamOutlined />}
                        type={isGuestMode ? 'primary' : 'default'}
                        onClick={() => setIsGuestMode(!isGuestMode)}
                      >
                        {isGuestMode ? '游客' : '用户'}
                      </Button>
                    </Tooltip>
                    <Tooltip title="查看提示词">
                      <Button
                        icon={<FileTextOutlined />}
                        onClick={fetchDebugMessages}
                        loading={debugLoading}
                      />
                    </Tooltip>
                    <Tooltip title="聊天历史">
                      <Button
                        icon={<HistoryOutlined />}
                        onClick={() => setShowHistory(true)}
                        disabled={chatHistory.length === 0}
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
                style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
                bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}
              >
                {/* 消息列表 */}
                <div
                  style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '16px',
                    backgroundColor: '#fafafa',
                    minHeight: 0,
                  }}
                >
                  {messages.length === 0 ? (
                    <Empty
                      description="还没有聊天记录，开始对话吧！"
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                    />
                  ) : (
                    <List
                      dataSource={messages}
                      renderItem={(message) => (
                        <List.Item
                          style={{
                            border: 'none',
                            padding: '8px 0',
                            justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                          }}
                        >
                          <div
                            style={{
                              maxWidth: '70%',
                              display: 'flex',
                              flexDirection: message.role === 'user' ? 'row-reverse' : 'row',
                              alignItems: 'flex-start',
                              gap: '8px',
                            }}
                          >
                            <Avatar
                              size="small"
                              icon={message.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                              src={message.role === 'assistant' ? selectedAgent.avatar : undefined}
                              style={{
                                backgroundColor: message.role === 'user' ? '#1890ff' : '#52c41a',
                                flexShrink: 0,
                              }}
                            />
                            <div
                              style={{
                                backgroundColor: message.role === 'user' ? '#1890ff' : '#fff',
                                color: message.role === 'user' ? '#fff' : '#000',
                                padding: '12px 16px',
                                borderRadius: '18px',
                                boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                                position: 'relative',
                                border: message.role === 'assistant' ? '1px solid #f0f0f0' : 'none',
                              }}
                              onMouseEnter={(e) => {
                                const actions = e.currentTarget.querySelector('.message-actions') as HTMLElement;
                                if (actions) actions.style.opacity = '1';
                              }}
                              onMouseLeave={(e) => {
                                const actions = e.currentTarget.querySelector('.message-actions') as HTMLElement;
                                if (actions) actions.style.opacity = '0';
                              }}
                            >
                              <Paragraph
                                style={{
                                  margin: 0,
                                  color: message.role === 'user' ? '#fff' : '#000',
                                  whiteSpace: 'pre-wrap',
                                  wordBreak: 'break-word',
                                }}
                              >
                                {message.role === 'assistant' ? formatMessageContent(message.content) : message.content}
                              </Paragraph>
                              <div
                                style={{
                                  fontSize: '10px',
                                  opacity: 0.7,
                                  marginTop: '4px',
                                  textAlign: message.role === 'user' ? 'right' : 'left',
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                }}
                              >
                                <span>
                                  <ClockCircleOutlined style={{ marginRight: '2px' }} />
                                  {new Date(message.timestamp).toLocaleTimeString()}
                                </span>
                                <div
                                  className="message-actions"
                                  style={{
                                    opacity: 0,
                                    transition: 'opacity 0.2s',
                                    display: 'flex',
                                    gap: '4px',
                                    alignItems: 'center',
                                  }}
                                >
                                  {/* 语音播放按钮 - 只对AI回复且有真实消息ID的消息显示 */}
                                  {message.role === 'assistant' && message.remoteId &&
                                    !message.remoteId.startsWith('assistant_') && !message.remoteId.startsWith('error_') &&
                                    !message.remoteId.startsWith('remote_') && selectedAgent && (
                                      <VoicePlayer
                                        agentId={selectedAgent.id}
                                        messageId={message.remoteId}
                                        messageText={message.content}
                                        language="zh"
                                        size="small"
                                        style={{
                                          color: '#666',
                                          padding: '2px 4px',
                                          height: 'auto',
                                          minWidth: 'auto',
                                        }}
                                      />
                                    )}

                                  {/* 只有历史消息才显示重新发送和删除按钮 */}
                                  {message.remoteId && !message.remoteId.startsWith('user_') &&
                                    !message.remoteId.startsWith('assistant_') && !message.remoteId.startsWith('error_') && (
                                      <>
                                        {message.role === 'user' && (
                                          <Tooltip title="重新发送">
                                            <Button
                                              type="text"
                                              size="small"
                                              icon={<RedoOutlined />}
                                              style={{
                                                color: message.role === 'user' ? '#fff' : '#666',
                                                padding: '2px 4px',
                                                height: 'auto',
                                                minWidth: 'auto',
                                              }}
                                              onClick={() => handleResendMessage(message)}
                                            />
                                          </Tooltip>
                                        )}
                                        <Tooltip title="删除消息">
                                          <Button
                                            type="text"
                                            size="small"
                                            icon={<DeleteOutlined />}
                                            style={{
                                              color: message.role === 'user' ? '#fff' : '#666',
                                              padding: '2px 4px',
                                              height: 'auto',
                                              minWidth: 'auto',
                                            }}
                                            onClick={() => handleDeleteMessage(message)}
                                          />
                                        </Tooltip>
                                      </>
                                    )}
                                </div>
                              </div>
                            </div>
                          </div>
                        </List.Item>
                      )}
                    />
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* 输入区域 */}
                <div style={{
                  padding: '16px',
                  backgroundColor: '#fff',
                  borderTop: '1px solid #f0f0f0',
                  flexShrink: 0
                }}>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end' }}>
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
                    <div style={{ marginTop: '8px', textAlign: 'center' }}>
                      <Spin size="small" />
                      <Text type="secondary" style={{ marginLeft: '8px' }}>
                        {selectedAgent.name} 正在思考中...
                      </Text>
                    </div>
                  )}
                </div>
              </Card>
            ) : (
              <Card style={{ height: '100%' }}>
                <div style={{ textAlign: 'center', padding: '100px 0' }}>
                  <Empty
                    description="请选择一个智能体开始聊天"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                </div>
              </Card>
            )}
          </Col>
        </Row>

        {/* 调试消息模态框 */}
        <Modal
          title="调试消息"
          open={debugModalVisible}
          onCancel={() => setDebugModalVisible(false)}
          footer={[
            <Button key="close" onClick={() => setDebugModalVisible(false)}>
              关闭
            </Button>
          ]}
          width={800}
          style={{ top: 50 }}
        >
          {debugData && debugData.debug_messages && (
            <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
              {debugData.debug_messages.messages.map((msg: any, index: number) => (
                <div key={index} style={{ marginBottom: 16 }}>
                  <h4 style={{
                    margin: '8px 0',
                    fontSize: '14px',
                    fontWeight: 'bold',
                    color: msg.type === 'system' ? '#1890ff' : msg.type === 'human' ? '#52c41a' : '#fa8c16'
                  }}>
                    {msg.type === 'system' ? '系统消息' : msg.type === 'human' ? '用户消息' : 'AI回复'}
                  </h4>
                  <div
                    style={{
                      background: msg.type === 'system' ? '#f0f8ff' : msg.type === 'human' ? '#f6ffed' : '#fff7e6',
                      padding: '12px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      lineHeight: '1.6',
                      fontFamily: msg.type === 'system' ? 'monospace' : 'inherit',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      border: `1px solid ${msg.type === 'system' ? '#d4edda' : msg.type === 'human' ? '#b7eb8f' : '#ffd591'}`
                    }}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}

              {/* 原始JSON数据显示 */}
              <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid #f0f0f0' }}>
                <h4 style={{ margin: '8px 0', fontSize: '14px', fontWeight: 'bold', color: '#666' }}>
                  原始JSON数据
                </h4>
                <div
                  style={{
                    background: '#f5f5f5',
                    padding: '12px',
                    borderRadius: '6px',
                    fontSize: '11px',
                    lineHeight: '1.4',
                    fontFamily: 'monospace',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    border: '1px solid #e0e0e0',
                    maxHeight: '300px',
                    overflowY: 'auto'
                  }}
                >
                  {JSON.stringify(debugData.debug_messages.messages, null, 2)}
                </div>
              </div>
            </div>
          )}
        </Modal>

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
          width={800}
        >
          <List
            dataSource={chatHistory}
            renderItem={(session) => (
              <List.Item
                key={session.id}
                actions={[
                  <Button
                    key="load"
                    type="link"
                    onClick={() => {
                      setCurrentSession(session);
                      setMessages(session.messages);
                      setShowHistory(false);
                      message.success('已加载历史会话');
                    }}
                  >
                    加载
                  </Button>,
                  <Button
                    key="delete"
                    type="link"
                    danger
                    onClick={() => {
                      Modal.confirm({
                        title: '确认删除',
                        content: '确定要删除这个聊天历史吗？',
                        okText: '确定',
                        cancelText: '取消',
                        onOk: () => {
                          const updatedHistory = chatHistory.filter(h => h.id !== session.id);
                          setChatHistory(updatedHistory);
                          saveChatHistory(updatedHistory);
                          message.success('历史记录已删除');
                        },
                      });
                    }}
                  >
                    删除
                  </Button>
                ]}
              >
                <List.Item.Meta
                  avatar={<Avatar icon={<MessageOutlined />} />}
                  title={`与 ${session.agent_name} 的对话`}
                  description={
                    <div>
                      <Text type="secondary">
                        {session.messages.length} 条消息 |
                        创建时间: {new Date(session.created_at).toLocaleString()}
                      </Text>
                      {session.messages.length > 0 && (
                        <div style={{ marginTop: 4 }}>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            最后一条: {session.messages[session.messages.length - 1]?.content?.slice(0, 50)}...
                          </Text>
                        </div>
                      )}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        </Modal>
      </Content>
    </Layout>
  );
};