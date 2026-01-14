/**
 * 用户每日聊天记录查询页面
 * 通过邮箱或用户 ID 查询用户的每日聊天记录和当日统计，并可查看每个会话的详细对话历史
 */

import React, { useState, useCallback } from "react";
import {
  Card,
  DatePicker,
  Select,
  Button,
  Space,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Input,
  message,
  Spin,
  Empty,
  Pagination,
} from "antd";
import {
  SearchOutlined,
  UserOutlined,
  MessageOutlined,
  CalendarOutlined,
  DownloadOutlined,
} from "@ant-design/icons";
import Plot from "react-plotly.js";
import type { ColumnsType } from "antd/es/table";
import dayjs, { Dayjs } from "dayjs";
import { userAnalyticsApi } from "../services/api";
import {
  formatUtcTime,
  formatUtcTimeRaw,
  getCurrentUtcTime,
} from "../utils/dateUtils";
import type {
  UserDailyMessagesResponse,
  UserTodayStatsResponse,
  SessionMessagesResponse,
  UserDailyMessageItem,
  UserSessionItem,
  SessionMessageItem,
} from "../types";

const { RangePicker } = DatePicker;
const { Option } = Select;

export const UserDailyMessagesPage: React.FC = () => {
  // 查询表单状态
  const [searchType, setSearchType] = useState<"email" | "user_id">("email");
  const [searchValue, setSearchValue] = useState<string>("");
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);

  // 数据加载状态
  const [loading, setLoading] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState<
    Record<string, boolean>
  >({});
  const [exportingSessions, setExportingSessions] = useState<
    Record<string, boolean>
  >({});

  // 数据状态
  const [userInfo, setUserInfo] = useState<UserDailyMessagesResponse | null>(
    null,
  );
  const [todayStats, setTodayStats] = useState<UserTodayStatsResponse | null>(
    null,
  );
  const [sessions, setSessions] = useState<UserSessionItem[]>([]);
  const [sessionMessages, setSessionMessages] = useState<
    Record<string, SessionMessagesResponse>
  >({});
  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(
    new Set(),
  );

  // 查询用户每日消息
  const handleSearch = useCallback(async () => {
    const trimmed = searchValue.trim();
    if (!trimmed) {
      message.warning(
        searchType === "email" ? "请输入用户邮箱" : "请输入用户ID",
      );
      return;
    }

    setLoading(true);
    try {
      const identifierParams =
        searchType === "email" ? { email: trimmed } : { user_id: trimmed };

      const params: typeof identifierParams & {
        start_date?: string;
        end_date?: string;
      } = { ...identifierParams };

      if (dateRange && dateRange[0] && dateRange[1]) {
        params.start_date = dateRange[0].format("YYYY-MM-DD");
        params.end_date = dateRange[1].format("YYYY-MM-DD");
      }

      const [dailyMessagesData, todayStatsData] = await Promise.all([
        userAnalyticsApi.getUserDailyMessages(params),
        userAnalyticsApi.getUserTodayStats(identifierParams),
      ]);

      setUserInfo(dailyMessagesData);
      setTodayStats(todayStatsData);

      // 自动加载会话列表
      try {
        const sessionsData =
          await userAnalyticsApi.getUserSessions(identifierParams);
        setSessions(sessionsData.sessions);
      } catch (error: any) {
        console.error("加载会话列表失败:", error);
        // 不显示错误，因为这不是主要功能
      }

      message.success("查询成功");
    } catch (error: any) {
      console.error("查询失败:", error);
      message.error(error?.message || "查询失败");
      setUserInfo(null);
      setTodayStats(null);
    } finally {
      setLoading(false);
    }
  }, [searchType, searchValue, dateRange]);

  // 加载会话列表
  const loadSessions = useCallback(async () => {
    const trimmed = searchValue.trim();
    if (!trimmed) {
      return;
    }

    setLoadingSessions(true);
    try {
      const identifierParams =
        searchType === "email" ? { email: trimmed } : { user_id: trimmed };
      const data = await userAnalyticsApi.getUserSessions(identifierParams);
      setSessions(data.sessions);
    } catch (error: any) {
      console.error("加载会话列表失败:", error);
      message.error(error?.message || "加载会话列表失败");
    } finally {
      setLoadingSessions(false);
    }
  }, [searchType, searchValue]);

  // 加载会话消息
  const loadSessionMessages = useCallback(
    async (chatId: string, page: number = 1) => {
      setLoadingMessages((prev) => ({ ...prev, [chatId]: true }));
      try {
        const data = await userAnalyticsApi.getSessionMessages({
          chat_id: chatId,
          page,
          size: 50,
        });
        setSessionMessages((prev) => ({
          ...prev,
          [chatId]: data,
        }));
      } catch (error: any) {
        console.error("加载会话消息失败:", error);
        message.error(error?.message || "加载会话消息失败");
      } finally {
        setLoadingMessages((prev) => ({ ...prev, [chatId]: false }));
      }
    },
    [],
  );

  // 处理会话展开/收起
  const handleSessionExpand = useCallback(
    (chatId: string, expanded: boolean) => {
      const newExpanded = new Set(expandedSessions);
      if (expanded) {
        newExpanded.add(chatId);
        // 如果还没有加载过消息，则加载
        if (!sessionMessages[chatId]) {
          loadSessionMessages(chatId);
        }
      } else {
        newExpanded.delete(chatId);
      }
      setExpandedSessions(newExpanded);
    },
    [expandedSessions, sessionMessages, loadSessionMessages],
  );

  // 处理消息分页
  const handleMessagePageChange = useCallback(
    (chatId: string, page: number) => {
      loadSessionMessages(chatId, page);
    },
    [loadSessionMessages],
  );

  // 导出会话历史记录
  const handleExportSession = useCallback(
    async (chatId: string, agentName: string, session: UserSessionItem) => {
      setExportingSessions((prev) => ({ ...prev, [chatId]: true }));
      try {
        // 分页获取所有消息
        const allMessages: SessionMessageItem[] = [];
        let page = 1;
        let hasMore = true;
        const pageSize = 50;

        while (hasMore) {
          const data = await userAnalyticsApi.getSessionMessages({
            chat_id: chatId,
            page,
            size: pageSize,
          });

          allMessages.push(...data.messages);
          hasMore = data.has_more;
          page++;
        }

        if (allMessages.length === 0) {
          message.warning("该会话暂无消息记录");
          return;
        }

        // 按时间排序
        allMessages.sort((a, b) => {
          const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
          const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
          return timeA - timeB;
        });

        // 格式化消息为 TXT
        const lines: string[] = [];
        lines.push("会话导出记录");
        lines.push("====================");
        lines.push(`角色名称: ${agentName}`);
        lines.push(`会话ID: ${chatId}`);
        lines.push(`创建时间: ${formatUtcTime(session.created_at)}`);
        lines.push(`更新时间: ${formatUtcTime(session.updated_at)}`);
        lines.push(`消息总数: ${allMessages.length}`);
        lines.push("");
        lines.push("对话记录");
        lines.push("====================");
        lines.push("");

        allMessages.forEach((msg) => {
          const timestamp = formatUtcTime(msg.created_at);
          const isUser =
            msg.message_type === "human" || msg.message_type === "HumanMessage";
          const sender = isUser ? "👤 用户" : "🤖 AI";

          lines.push(`[${timestamp}] ${sender}`);
          lines.push("");

          // 处理消息内容
          if (msg.message_type === "image" && msg.image_url) {
            lines.push(`[图片消息]`);
            lines.push(`图片URL: ${msg.image_url}`);
          } else if (msg.content) {
            lines.push(msg.content);
          } else {
            lines.push("[无文本内容]");
          }

          // 处理语音消息
          if (msg.audio_url) {
            lines.push("");
            lines.push(`[语音消息]`);
            lines.push(`语音URL: ${msg.audio_url}`);
          }

          // 处理生成的图片
          if (msg.meta_data?.generated_image?.image_url) {
            lines.push("");
            lines.push(`[生成的图片]`);
            lines.push(`图片URL: ${msg.meta_data.generated_image.image_url}`);
            if (
              msg.meta_data.generated_image.width &&
              msg.meta_data.generated_image.height
            ) {
              lines.push(
                `尺寸: ${msg.meta_data.generated_image.width} × ${msg.meta_data.generated_image.height}`,
              );
            }
          }

          lines.push("");
          lines.push("---");
          lines.push("");
        });

        // 生成文件名（处理特殊字符）
        const sanitizeFileName = (name: string) => {
          return name.replace(/[<>:"/\\|?*]/g, "_");
        };

        const timestamp = getCurrentUtcTime();
        const safeAgentName = sanitizeFileName(agentName);
        const safeChatId = chatId.substring(0, 20); // 限制长度
        const filename = `session_${safeAgentName}_${safeChatId}_${timestamp}.txt`;

        // 创建并下载文件
        const content = lines.join("\n");
        const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        message.success(`会话记录已导出: ${filename}`);
      } catch (error: any) {
        console.error("导出会话记录失败:", error);
        message.error(error?.message || "导出失败，请重试");
      } finally {
        setExportingSessions((prev) => ({ ...prev, [chatId]: false }));
      }
    },
    [],
  );

  // 每日消息表格列
  const dailyMessagesColumns: ColumnsType<UserDailyMessageItem> = [
    {
      title: "日期",
      dataIndex: "date",
      key: "date",
      width: 150,
    },
    {
      title: "消息数",
      dataIndex: "message_count",
      key: "message_count",
      width: 120,
      sorter: (a, b) => a.message_count - b.message_count,
    },
    {
      title: "会话数",
      dataIndex: "session_count",
      key: "session_count",
      width: 120,
      sorter: (a, b) => a.session_count - b.session_count,
    },
  ];

  // 会话表格列
  const sessionsColumns: ColumnsType<UserSessionItem> = [
    {
      title: "角色名称",
      dataIndex: "agent_name",
      key: "agent_name",
      width: 200,
    },
    {
      title: "消息数",
      dataIndex: "message_count",
      key: "message_count",
      width: 100,
      sorter: (a, b) => a.message_count - b.message_count,
    },
    {
      title: "创建时间 (UTC)",
      dataIndex: "created_at",
      key: "created_at",
      width: 200,
      render: (text: string) => formatUtcTimeRaw(text),
    },
    {
      title: "更新时间 (UTC)",
      dataIndex: "updated_at",
      key: "updated_at",
      width: 200,
      render: (text: string) => formatUtcTimeRaw(text),
    },
    {
      title: "操作",
      key: "action",
      width: 100,
      render: (_: any, record: UserSessionItem) => (
        <Button
          type="link"
          icon={<DownloadOutlined />}
          loading={exportingSessions[record.chat_id]}
          onClick={() =>
            handleExportSession(record.chat_id, record.agent_name, record)
          }
        >
          导出
        </Button>
      ),
    },
  ];

  // 计算总消息数
  const totalMessages =
    userInfo?.daily_messages.reduce(
      (sum, item) => sum + item.message_count,
      0,
    ) || 0;

  return (
    <div style={{ padding: "24px" }}>
      {/* 查询表单 */}
      <Card style={{ marginBottom: "24px" }}>
        <Space direction="vertical" style={{ width: "100%" }} size="large">
          <Space>
            <span>查询方式：</span>
            <Select
              value={searchType}
              onChange={(value) => setSearchType(value)}
              style={{ width: 120 }}
            >
              <Option value="email">邮箱</Option>
              <Option value="user_id">用户ID</Option>
            </Select>
            <span>查询值：</span>
            <Input
              placeholder={
                searchType === "email" ? "请输入用户邮箱" : "请输入用户ID"
              }
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              style={{ width: 300 }}
              onPressEnter={handleSearch}
            />
            <span>日期范围（可选）：</span>
            <RangePicker
              value={dateRange}
              onChange={(dates) => setDateRange(dates as [Dayjs, Dayjs] | null)}
              format="YYYY-MM-DD"
            />
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={handleSearch}
              loading={loading}
            >
              查询
            </Button>
            {userInfo && (
              <Button onClick={loadSessions} loading={loadingSessions}>
                加载会话列表
              </Button>
            )}
          </Space>
        </Space>
      </Card>

      {userInfo && (
        <>
          {/* 用户信息卡片 */}
          <Card style={{ marginBottom: "24px" }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="用户ID"
                  value={userInfo.user_id}
                  prefix={<UserOutlined />}
                  valueStyle={{ fontSize: "14px" }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="邮箱"
                  value={userInfo.email || "N/A"}
                  prefix={<UserOutlined />}
                  valueStyle={{ fontSize: "14px" }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="昵称"
                  value={userInfo.nickname || "N/A"}
                  prefix={<UserOutlined />}
                  valueStyle={{ fontSize: "14px" }}
                />
              </Col>
              <Col span={6}>
                <div>
                  <div
                    style={{ marginBottom: 4, color: "rgba(0, 0, 0, 0.45)" }}
                  >
                    认证类型
                  </div>
                  <Tag
                    color={userInfo.auth_type === "GOOGLE" ? "blue" : "orange"}
                  >
                    {userInfo.auth_type}
                  </Tag>
                </div>
              </Col>
            </Row>
            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col span={6}>
                <div>
                  <div
                    style={{ marginBottom: 4, color: "rgba(0, 0, 0, 0.45)" }}
                  >
                    性别
                  </div>
                  {userInfo.gender ? (
                    <Tag
                      color={
                        userInfo.gender === "MALE"
                          ? "blue"
                          : userInfo.gender === "FEMALE"
                            ? "pink"
                            : "default"
                      }
                    >
                      {userInfo.gender === "MALE"
                        ? "男"
                        : userInfo.gender === "FEMALE"
                          ? "女"
                          : "其他"}
                    </Tag>
                  ) : (
                    <span style={{ color: "rgba(0, 0, 0, 0.25)" }}>未设置</span>
                  )}
                </div>
              </Col>
              <Col span={6}>
                <Statistic
                  title="年龄段"
                  value={userInfo.age_group || "未设置"}
                  valueStyle={{
                    fontSize: "14px",
                    color: userInfo.age_group
                      ? "inherit"
                      : "rgba(0, 0, 0, 0.25)",
                  }}
                />
              </Col>
              {userInfo.created_at && (
                <Col span={12}>
                  <Statistic
                    title="注册时间 (UTC)"
                    value={formatUtcTimeRaw(userInfo.created_at)}
                    prefix={<CalendarOutlined />}
                    valueStyle={{ fontSize: "14px" }}
                  />
                </Col>
              )}
            </Row>
          </Card>

          {/* 当日统计卡片 */}
          {todayStats && (
            <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
              <Col xs={24} sm={12} md={8}>
                <Card>
                  <Statistic
                    title="今日消息数"
                    value={todayStats.today_message_count}
                    prefix={<MessageOutlined />}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={8}>
                <Card>
                  <Statistic
                    title="今日会话数"
                    value={todayStats.today_session_count}
                    prefix={<MessageOutlined />}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={8}>
                <Card>
                  <Statistic
                    title="总消息数"
                    value={totalMessages}
                    prefix={<MessageOutlined />}
                  />
                </Card>
              </Col>
            </Row>
          )}

          {/* 每日消息统计图表 */}
          {userInfo.daily_messages.length > 0 && (
            <Card title="每日消息趋势" style={{ marginBottom: "24px" }}>
              <Plot
                data={[
                  {
                    x: userInfo.daily_messages.map((d) => d.date),
                    y: userInfo.daily_messages.map((d) => d.message_count),
                    type: "bar",
                    marker: { color: "lightblue" },
                  },
                ]}
                layout={{
                  title: "每日消息趋势",
                  height: 400,
                  xaxis: { title: "日期" },
                  yaxis: { title: "消息数" },
                }}
                style={{ width: "100%", height: "100%" }}
              />
            </Card>
          )}

          {/* 每日消息统计表格 */}
          <Card title="每日消息统计" style={{ marginBottom: "24px" }}>
            <Table
              columns={dailyMessagesColumns}
              dataSource={userInfo.daily_messages}
              rowKey="date"
              loading={loading}
              pagination={false}
              summary={() => {
                const totalSessions =
                  userInfo?.daily_messages.reduce(
                    (sum, item) => sum + item.session_count,
                    0,
                  ) || 0;
                return (
                  <Table.Summary fixed>
                    <Table.Summary.Row>
                      <Table.Summary.Cell index={0}>总计</Table.Summary.Cell>
                      <Table.Summary.Cell index={1}>
                        <strong>{totalMessages}</strong>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={2}>
                        <strong>{totalSessions}</strong>
                      </Table.Summary.Cell>
                    </Table.Summary.Row>
                  </Table.Summary>
                );
              }}
            />
          </Card>

          {/* 会话列表和对话历史 */}
          <Card
            title="会话列表和对话历史"
            style={{ marginBottom: "24px" }}
            extra={
              sessions.length > 0 && (
                <span style={{ fontSize: "12px", color: "#666" }}>
                  点击行展开查看对话记录
                </span>
              )
            }
          >
            {sessions.length > 0 ? (
              <Table
                columns={sessionsColumns}
                dataSource={sessions}
                rowKey="chat_id"
                loading={loadingSessions}
                pagination={false}
                expandable={{
                  expandedRowKeys: Array.from(expandedSessions),
                  onExpand: (expanded, record) => {
                    handleSessionExpand(record.chat_id, expanded);
                  },
                  expandedRowRender: (record) => {
                    const messagesData = sessionMessages[record.chat_id];
                    const isLoading = loadingMessages[record.chat_id];

                    if (isLoading) {
                      return (
                        <div style={{ textAlign: "center", padding: "20px" }}>
                          <Spin />
                        </div>
                      );
                    }

                    if (!messagesData || messagesData.messages.length === 0) {
                      return <Empty description="暂无消息" />;
                    }

                    return (
                      <div style={{ padding: "16px" }}>
                        {messagesData.messages.map(
                          (msg: SessionMessageItem) => (
                            <div
                              key={msg.id}
                              style={{
                                marginBottom: 12,
                                padding: 12,
                                backgroundColor:
                                  msg.message_type === "human" ||
                                  msg.message_type === "HumanMessage"
                                    ? "#e6f7ff"
                                    : "#f0f0f0",
                                borderRadius: 8,
                                textAlign:
                                  msg.message_type === "human" ||
                                  msg.message_type === "HumanMessage"
                                    ? "right"
                                    : "left",
                                maxWidth: "80%",
                                marginLeft:
                                  msg.message_type === "human" ||
                                  msg.message_type === "HumanMessage"
                                    ? "auto"
                                    : 0,
                                marginRight:
                                  msg.message_type === "human" ||
                                  msg.message_type === "HumanMessage"
                                    ? 0
                                    : "auto",
                              }}
                            >
                              <div
                                style={{
                                  fontSize: 12,
                                  color: "#666",
                                  marginBottom: 4,
                                }}
                              >
                                {msg.message_type === "human" ||
                                msg.message_type === "HumanMessage"
                                  ? "👤 用户"
                                  : "🤖 AI"}{" "}
                                •{" "}
                                {msg.created_at
                                  ? formatUtcTimeRaw(msg.created_at)
                                  : ""}
                              </div>
                              <div
                                style={{
                                  wordBreak: "break-word",
                                  whiteSpace: "pre-wrap",
                                }}
                              >
                                {msg.content ? (
                                  msg.content.length > 1000 ? (
                                    <span>
                                      {msg.content.substring(0, 1000)}...
                                      <span
                                        style={{
                                          color: "#999",
                                          fontSize: "12px",
                                        }}
                                      >
                                        （内容过长，已截断）
                                      </span>
                                    </span>
                                  ) : (
                                    msg.content
                                  )
                                ) : (
                                  <span
                                    style={{
                                      color: "#999",
                                      fontStyle: "italic",
                                    }}
                                  >
                                    无文本内容
                                  </span>
                                )}
                              </div>
                              {msg.audio_url && (
                                <div style={{ marginTop: 4 }}>
                                  <Tag color="purple">语音消息</Tag>
                                </div>
                              )}
                              {/* 显示独立图片消息（type="image"） */}
                              {msg.message_type === "image" &&
                                msg.image_url && (
                                  <div style={{ marginTop: 8 }}>
                                    <img
                                      src={msg.image_url}
                                      alt="图片消息"
                                      style={{
                                        maxWidth: "100%",
                                        maxHeight: "400px",
                                        borderRadius: 8,
                                        border: "1px solid #e0e0e0",
                                      }}
                                      onError={(e) => {
                                        // 图片加载失败时的处理
                                        (
                                          e.target as HTMLImageElement
                                        ).style.display = "none";
                                      }}
                                    />
                                  </div>
                                )}
                              {/* 显示文本消息中包含的生成图片（meta_data.generated_image） */}
                              {msg.meta_data?.generated_image?.image_url && (
                                <div style={{ marginTop: 8 }}>
                                  <img
                                    src={
                                      msg.meta_data.generated_image.image_url
                                    }
                                    alt="生成的图片"
                                    style={{
                                      maxWidth: "100%",
                                      maxHeight: "400px",
                                      borderRadius: 8,
                                      border: "1px solid #e0e0e0",
                                    }}
                                    onError={(e) => {
                                      // 图片加载失败时的处理
                                      (
                                        e.target as HTMLImageElement
                                      ).style.display = "none";
                                    }}
                                  />
                                  {msg.meta_data.generated_image.width &&
                                    msg.meta_data.generated_image.height && (
                                      <div
                                        style={{
                                          fontSize: "12px",
                                          color: "#999",
                                          marginTop: 4,
                                        }}
                                      >
                                        尺寸:{" "}
                                        {msg.meta_data.generated_image.width} ×{" "}
                                        {msg.meta_data.generated_image.height}
                                      </div>
                                    )}
                                </div>
                              )}
                            </div>
                          ),
                        )}
                        {messagesData.has_more && (
                          <div style={{ textAlign: "center", marginTop: 16 }}>
                            <Pagination
                              current={messagesData.page}
                              total={messagesData.total}
                              pageSize={messagesData.size}
                              onChange={(page) =>
                                handleMessagePageChange(record.chat_id, page)
                              }
                              showSizeChanger={false}
                            />
                          </div>
                        )}
                      </div>
                    );
                  },
                }}
              />
            ) : (
              <Empty
                description={
                  loadingSessions
                    ? "加载中..."
                    : "暂无会话数据，会话列表会在查询用户信息后自动加载"
                }
              />
            )}
          </Card>
        </>
      )}

      {!userInfo && !loading && (
        <Card>
          <Empty description="请输入用户邮箱或用户ID并点击查询" />
        </Card>
      )}
    </div>
  );
};
