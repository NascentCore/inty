/**
 * 会话提示词查询页面
 * 复刻inty-test中的会话提示词查询功能
 */

import React, { useState, useEffect, useCallback } from "react";
import {
  Card,
  Row,
  Col,
  Select,
  Button,
  Input,
  Collapse,
  Tag,
  Typography,
  Empty,
  Spin,
  message,
  Space,
  Divider,
  Avatar,
} from "antd";
import {
  SearchOutlined,
  UserOutlined,
  RobotOutlined,
  MessageOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import api from "../services/api";
import type { Agent } from "../types";

const { Panel } = Collapse;
const { Text, Title } = Typography;
const { Option } = Select;

// 调试消息接口定义
interface DebugMessage {
  type: string; // 'system', 'character', 'user'
  content: string;
}

interface DebugMessagesData {
  chat_id: string;
  user_id: string;
  user_nickname: string;
  agent_id: string;
  agent_name: string;
  debug_messages: {
    messages: DebugMessage[];
    timestamp: number;
    agent_id: string;
    user_id: string;
    session_id: string;
  };
  created_at: string;
  updated_at: string;
}

interface User {
  id: string;
  readable_id: string;
  nickname: string;
  avatar?: string;
}

// 防抖函数
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
): (...args: Parameters<T>) => void {
  let timeout: any;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

export const PromptQueryPage: React.FC = () => {
  // 状态管理
  const [users, setUsers] = useState<User[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [userSearchText, setUserSearchText] = useState("");
  const [queryResults, setQueryResults] = useState<DebugMessagesData[]>([]);

  // 加载状态
  const [usersLoading, setUsersLoading] = useState(false);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [queryLoading, setQueryLoading] = useState(false);

  // 加载用户列表
  const loadUsers = useCallback(async (search?: string) => {
    try {
      setUsersLoading(true);

      // 使用真实的用户搜索API
      try {
        const response = await api.users.searchUsers({
          search: search,
          skip: 0,
          limit: 50,
        });

        console.log("用户API响应:", response);

        // 尝试不同的响应格式
        let userList: User[] = [];
        if (response.users) {
          userList = response.users;
        } else if (response.items && Array.isArray(response.items)) {
          userList = response.items;
        } else if (Array.isArray(response)) {
          userList = response;
        } else if (response.data && Array.isArray(response.data)) {
          userList = response.data;
        }

        setUsers(userList);
        console.log(`加载用户列表成功，共 ${userList.length} 个用户`);
        return;
      } catch (apiError) {
        console.warn("用户API调用失败，尝试备用API:", apiError);

        // 尝试使用 getUsers API
        try {
          const userList = await api.users.getUsers({
            search: search,
            skip: 0,
            limit: 50,
          });

          console.log("用户备用API响应:", userList);
          setUsers(Array.isArray(userList) ? userList : []);
          console.log(
            `使用备用API加载用户列表成功，共 ${Array.isArray(userList) ? userList.length : 0} 个用户`,
          );
          return;
        } catch (fallbackError) {
          console.warn("备用API也失败:", fallbackError);
        }
      }
    } catch (error) {
      console.error("加载用户列表失败:", error);
    }

    // 如果所有API都失败，使用本地备用用户列表
    const fallbackUsers: User[] = [
      {
        id: "user-01JWZ34Y4D1C92GD86A5R6EWYJ",
        readable_id: "admin",
        nickname: "管理员",
      },
      {
        id: "guest-user-1",
        readable_id: "guest-001",
        nickname: "游客用户1",
      },
      {
        id: "guest-user-2",
        readable_id: "guest-002",
        nickname: "游客用户2",
      },
    ];

    let filteredUsers = fallbackUsers;
    if (search) {
      filteredUsers = fallbackUsers.filter(
        (user) =>
          user.nickname.toLowerCase().includes(search.toLowerCase()) ||
          user.readable_id.toLowerCase().includes(search.toLowerCase()),
      );
    }

    setUsers(filteredUsers);
    message.info("使用本地用户列表，请检查后端用户接口");
    setUsersLoading(false);
  }, []);

  // 防抖搜索用户
  const debouncedLoadUsers = useCallback(
    debounce((search: string) => {
      loadUsers(search.trim() || undefined);
    }, 500),
    [loadUsers],
  );

  // 加载AI角色列表
  const loadAgents = useCallback(async () => {
    try {
      setAgentsLoading(true);
      const agentList = await api.agents.list({ limit: 100 });
      setAgents(agentList || []);
    } catch (error) {
      console.error("加载AI角色列表失败:", error);
      message.error("加载AI角色列表失败");
    } finally {
      setAgentsLoading(false);
    }
  }, []);

  // 查询提示词
  const queryPrompts = useCallback(async () => {
    if (!selectedUserId && !selectedAgentId) {
      message.warning("请至少选择一个用户或AI角色");
      return;
    }

    try {
      setQueryLoading(true);

      console.log("开始查询提示词:", {
        selectedUserId,
        selectedAgentId,
        userInfo: users.find((u) => u.id === selectedUserId),
        agentInfo: agents.find((a) => a.id === selectedAgentId),
      });

      // 优先使用专门的调试消息API
      try {
        const params = {
          user_id: selectedUserId || undefined,
          agent_id: selectedAgentId || undefined,
          skip: 0,
          limit: 20,
        };

        console.log("调用调试消息API，参数:", params);
        const debugResults = await api.debug.getDebugMessages(params);
        console.log("调试消息API响应:", debugResults);

        // 根据实际API响应格式解析数据
        let results: DebugMessagesData[] = [];
        if (
          debugResults &&
          debugResults.items &&
          Array.isArray(debugResults.items)
        ) {
          results = debugResults.items;
        } else if (Array.isArray(debugResults)) {
          // 兼容旧格式
          results = debugResults;
        }

        setQueryResults(results);
        message.success(`查询成功，找到 ${results.length} 条记录`);
        return;
      } catch (debugError) {
        console.warn("调试消息API调用失败，尝试使用备用方案:", debugError);
      }

      // 备用方案：如果有选择的Agent，尝试获取其调试消息
      if (selectedAgentId) {
        console.log("使用备用方案，调用单个Agent调试消息API:", selectedAgentId);
        const debugData = await api.chat.getAgentDebugMessages(selectedAgentId);
        console.log("Agent调试消息API响应:", debugData);

        // 转换数据格式以匹配界面显示
        const formattedResults: DebugMessagesData[] = [
          {
            chat_id: `chat-${selectedAgentId}`,
            user_id: selectedUserId || "unknown",
            user_nickname:
              users.find((u) => u.id === selectedUserId)?.nickname ||
              "未知用户",
            agent_id: selectedAgentId,
            agent_name:
              agents.find((a) => a.id === selectedAgentId)?.name || "未知角色",
            debug_messages: {
              messages: Array.isArray(debugData.messages)
                ? debugData.messages.map((msg: any) => ({
                    type: msg.type || msg.role || "unknown",
                    content: msg.content || "",
                  }))
                : [],
              timestamp: debugData.timestamp || Date.now(),
              agent_id: selectedAgentId,
              user_id: selectedUserId || "unknown",
              session_id: debugData.session_id || `session-${Date.now()}`,
            },
            created_at: debugData.created_at || new Date().toISOString(),
            updated_at: debugData.updated_at || new Date().toISOString(),
          },
        ];

        setQueryResults(formattedResults);
        message.success(`查询成功，找到 ${formattedResults.length} 条记录`);
      } else {
        setQueryResults([]);
        message.info("暂无匹配的记录");
      }
    } catch (error) {
      console.error("查询提示词失败:", error);
      message.error("查询失败，请重试");
      setQueryResults([]);
    } finally {
      setQueryLoading(false);
    }
  }, [selectedUserId, selectedAgentId, users, agents]);

  // 组件初始化
  useEffect(() => {
    loadUsers();
    loadAgents();
  }, []); // 移除依赖，只在组件挂载时执行一次

  // 用户搜索处理
  useEffect(() => {
    if (userSearchText) {
      debouncedLoadUsers(userSearchText);
    }
    // 不在这里重新加载完整列表，避免在用户选择后触发重复请求
  }, [userSearchText]);

  // 获取消息类型标签颜色
  const getMessageTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case "system":
        return "blue";
      case "character":
      case "assistant":
        return "green";
      case "user":
        return "orange";
      default:
        return "default";
    }
  };

  // 获取消息类型显示名称
  const getMessageTypeName = (type: string) => {
    switch (type.toLowerCase()) {
      case "system":
        return "系统消息";
      case "character":
      case "assistant":
        return "角色消息";
      case "user":
        return "用户消息";
      default:
        return type;
    }
  };

  // 渲染查询结果
  const renderQueryResults = () => {
    // 确保 queryResults 是数组
    const results = Array.isArray(queryResults) ? queryResults : [];

    if (results.length === 0) {
      return (
        <Empty
          description="暂无查询结果"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      );
    }

    return (
      <Collapse ghost>
        {results.map((result, index) => (
          <Panel
            key={`${result.chat_id}-${index}`}
            header={
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <Avatar
                  size="small"
                  icon={<UserOutlined />}
                  src={users.find((u) => u.id === result.user_id)?.avatar}
                />
                <Text strong>{result.user_nickname}</Text>
                <Text type="secondary">与</Text>
                <Avatar
                  size="small"
                  icon={<RobotOutlined />}
                  src={agents.find((a) => a.id === result.agent_id)?.avatar}
                />
                <Text strong>{result.agent_name}</Text>
                <Text type="secondary">的会话</Text>
                <Text type="secondary" style={{ marginLeft: "auto" }}>
                  {new Date(result.created_at).toLocaleString()}
                </Text>
              </div>
            }
          >
            <div style={{ padding: "16px 0" }}>
              {result.debug_messages &&
              result.debug_messages.messages &&
              Array.isArray(result.debug_messages.messages) &&
              result.debug_messages.messages.length > 0 ? (
                result.debug_messages.messages.map((msg, msgIndex) => (
                  <div key={msgIndex} style={{ marginBottom: 16 }}>
                    <div style={{ marginBottom: 8 }}>
                      <Tag color={getMessageTypeColor(msg.type || "unknown")}>
                        {getMessageTypeName(msg.type || "unknown")}
                      </Tag>
                    </div>
                    <div
                      style={{
                        padding: "12px",
                        backgroundColor: "#f5f5f5",
                        borderRadius: "6px",
                        lineHeight: "1.6",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                      }}
                    >
                      {msg.content || "(无内容)"}
                    </div>
                  </div>
                ))
              ) : (
                <Empty
                  description="此会话暂无调试消息"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              )}
            </div>
          </Panel>
        ))}
      </Collapse>
    );
  };

  return (
    <div style={{ padding: "24px", background: "#f0f2f5", minHeight: "100vh" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>
        {/* 查询条件区域 */}
        <Card style={{ marginBottom: 24 }}>
          <Title level={4} style={{ marginBottom: 24 }}>
            <MessageOutlined style={{ marginRight: 8 }} />
            会话提示词查询
          </Title>

          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={8}>
              <div style={{ marginBottom: 8 }}>
                <Text strong>选择用户</Text>
              </div>
              <Select
                style={{ width: "100%" }}
                placeholder="请选择用户"
                showSearch
                allowClear
                searchValue={userSearchText}
                onSearch={setUserSearchText}
                onClear={() => {
                  setUserSearchText("");
                  loadUsers(); // 清除搜索时重新加载完整列表
                }}
                value={selectedUserId || undefined}
                onChange={setSelectedUserId}
                loading={usersLoading}
                filterOption={false}
                notFoundContent={
                  usersLoading ? <Spin size="small" /> : "暂无数据"
                }
              >
                {users.map((user) => (
                  <Option key={user.id} value={user.id}>
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 8 }}
                    >
                      <Avatar
                        size="small"
                        icon={<UserOutlined />}
                        src={user.avatar}
                        style={{ flexShrink: 0 }}
                      />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            fontWeight: 500,
                            color: "rgba(0, 0, 0, 0.85)",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {user.nickname || user.readable_id}
                        </div>
                        <div
                          style={{
                            fontSize: "12px",
                            color: "rgba(0, 0, 0, 0.45)",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          ID: {user.readable_id}
                        </div>
                      </div>
                    </div>
                  </Option>
                ))}
              </Select>
            </Col>

            <Col xs={24} sm={12} md={8}>
              <div style={{ marginBottom: 8 }}>
                <Text strong>选择AI角色</Text>
              </div>
              <Select
                style={{ width: "100%" }}
                placeholder="请选择AI角色"
                showSearch
                allowClear
                value={selectedAgentId || undefined}
                onChange={setSelectedAgentId}
                loading={agentsLoading}
                filterOption={(input, option) => {
                  const agent = agents.find((a) => a.id === option?.value);
                  return (
                    agent?.name.toLowerCase().includes(input.toLowerCase()) ||
                    false
                  );
                }}
                notFoundContent={
                  agentsLoading ? <Spin size="small" /> : "暂无数据"
                }
              >
                {agents.map((agent) => (
                  <Option key={agent.id} value={agent.id}>
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 8 }}
                    >
                      <Avatar
                        size="small"
                        icon={<RobotOutlined />}
                        src={agent.avatar}
                        style={{ flexShrink: 0 }}
                      />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            fontWeight: 500,
                            color: "rgba(0, 0, 0, 0.85)",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {agent.name}
                        </div>
                        {agent.intro && (
                          <div
                            style={{
                              fontSize: "12px",
                              color: "rgba(0, 0, 0, 0.45)",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {agent.intro.length > 30
                              ? `${agent.intro.substring(0, 30)}...`
                              : agent.intro}
                          </div>
                        )}
                      </div>
                    </div>
                  </Option>
                ))}
              </Select>
            </Col>

            <Col xs={24} sm={24} md={8}>
              <div style={{ marginBottom: 8 }}>
                <Text strong>操作</Text>
              </div>
              <Button
                type="primary"
                icon={<SearchOutlined />}
                loading={queryLoading}
                disabled={!selectedUserId && !selectedAgentId}
                onClick={queryPrompts}
                size="large"
                style={{ width: "100%" }}
              >
                查询提示词
              </Button>
            </Col>
          </Row>

          <Divider />

          <div style={{ textAlign: "center" }}>
            <Text type="secondary">
              请至少选择一个用户或AI角色进行查询，查询结果将显示相关的会话提示词信息
            </Text>
          </div>
        </Card>

        {/* 查询结果区域 */}
        <Card
          title={
            <Space>
              <HistoryOutlined />
              <span>查询结果</span>
              {Array.isArray(queryResults) && queryResults.length > 0 && (
                <Tag color="blue">{queryResults.length} 条记录</Tag>
              )}
            </Space>
          }
        >
          <Spin spinning={queryLoading}>{renderQueryResults()}</Spin>
        </Card>
      </div>
    </div>
  );
};

export default PromptQueryPage;
