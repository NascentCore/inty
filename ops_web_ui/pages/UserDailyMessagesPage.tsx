/**
 * 用户每日聊天记录查询页面
 * 通过邮箱或用户 ID 查询用户的每日聊天记录和当日统计，并可查看每个会话的详细对话历史
 */

import React, {
  useState,
  useCallback,
  useEffect,
  useMemo,
  useRef,
} from "react";
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
  Modal,
  Typography,
  Tooltip,
} from "antd";
import {
  SearchOutlined,
  UserOutlined,
  MessageOutlined,
  CalendarOutlined,
  DownloadOutlined,
  PictureOutlined,
  IdcardOutlined,
} from "@ant-design/icons";
import Plot from "react-plotly.js";
import type { ColumnsType } from "antd/es/table";
import type { Dayjs } from "dayjs";
import { agentApi, userAnalyticsApi } from "../services/api";
import { formatUtcTimeRaw, getCurrentUtcTime } from "../utils/dateUtils";
import { getLangsmithTraceUrl } from "../utils/langsmithUrl";
import {
  sessionMessagesPaginationProps,
  shouldShowSessionMessagesPagination,
} from "../utils/sessionMessagesPagination";
import { buildSessionExportContent } from "../utils/sessionExport";
import {
  countUserAgentConversationMessages,
  countUserAgentConversationSessions,
  filterSessionsWithMessages,
  isUserMessageType,
} from "../utils/userAgentConversations";
import { CollapsibleMessageContent } from "../components/CollapsibleMessageContent";
import type {
  Agent,
  ChatMessageResponse,
  PaginatedUserAgentConversationsResponse,
  UserAgentConversationItem,
  UserDailyMessagesResponse,
  UserTodayStatsResponse,
  SessionMessagesResponse,
  UserDailyMessageItem,
  UserSessionItem,
  SessionMessageItem,
  UserGeneratedImageItem,
} from "../types";
import { AgentDetailModal } from "../components/common/AgentDetailModal";
import { getDeepLinkedUserIdFromHash } from "../utils/profileLinks";

const { RangePicker } = DatePicker;
const { Option } = Select;
const { Text, Paragraph } = Typography;

export const UserDailyMessagesPage: React.FC = () => {
  // 查询表单状态
  const [searchType, setSearchType] = useState<"email" | "user_id">("email");
  const [searchValue, setSearchValue] = useState<string>("");
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);

  // 数据加载状态
  const [loading, setLoading] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [loadingAllUsersConversations, setLoadingAllUsersConversations] =
    useState(false);
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
  const [loadingUserImages, setLoadingUserImages] = useState(false);
  const [userImages, setUserImages] = useState<UserGeneratedImageItem[]>([]);
  const [userImagesTotal, setUserImagesTotal] = useState(0);
  const [allUsersConversationPage, setAllUsersConversationPage] =
    useState<PaginatedUserAgentConversationsResponse | null>(null);
  const [allUsersConversationQuery, setAllUsersConversationQuery] = useState<{
    activity_start_date?: string;
    activity_end_date?: string;
  } | null>(null);
  const [showImagesModal, setShowImagesModal] = useState(false);
  const [previewImage, setPreviewImage] =
    useState<UserGeneratedImageItem | null>(null);
  const [characterDetailOpen, setCharacterDetailOpen] = useState(false);
  const [characterDetailAgent, setCharacterDetailAgent] =
    useState<Agent | null>(null);
  const [characterDetailLoading, setCharacterDetailLoading] = useState(false);
  const deepLinkedUserId = useMemo(() => {
    if (typeof window === "undefined") {
      return "";
    }
    return getDeepLinkedUserIdFromHash(window.location.hash);
  }, []);
  const hasTriggeredDeepLinkSearchRef = useRef(false);

  const getErrorMessage = (error: unknown, fallback: string): string => {
    if (error instanceof Error && error.message) {
      return error.message;
    }
    if (
      typeof error === "object" &&
      error !== null &&
      "message" in error &&
      typeof (error as { message?: unknown }).message === "string"
    ) {
      return (error as { message: string }).message;
    }
    return fallback;
  };

  const loadAllUsersConversationPage = useCallback(
    async (
      page: number,
      queryParams: { activity_start_date?: string; activity_end_date?: string },
    ) => {
      const data =
        await userAnalyticsApi.getUserAgentConversationsDetailPaginated({
          ...queryParams,
          page,
          size: 10,
        });
      setAllUsersConversationPage(data);
    },
    [],
  );

  // 查询用户每日消息
  const handleSearch = useCallback(async () => {
    const trimmed = searchValue.trim();
    const hasIdentifier = Boolean(trimmed);
    const hasDateRange = Boolean(dateRange && dateRange[0] && dateRange[1]);
    if (!hasIdentifier && !hasDateRange) {
      message.warning("不输入用户ID/邮箱时，请选择日期范围");
      return;
    }

    setLoading(true);
    try {
      const params: {
        email?: string;
        user_id?: string;
        start_date?: string;
        end_date?: string;
      } = {};

      if (hasIdentifier) {
        if (searchType === "email") {
          params.email = trimmed;
        } else {
          params.user_id = trimmed;
        }
      }

      if (dateRange && dateRange[0] && dateRange[1]) {
        params.start_date = dateRange[0].format("YYYY-MM-DD");
        params.end_date = dateRange[1].format("YYYY-MM-DD");
      }

      if (hasIdentifier) {
        const identifierParams =
          searchType === "email" ? { email: trimmed } : { user_id: trimmed };
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
        } catch (error: unknown) {
          console.error("加载会话列表失败:", error);
          // 不显示错误，因为这不是主要功能
        }
        setAllUsersConversationPage(null);
        setAllUsersConversationQuery(null);
      } else {
        const conversationQuery = {
          activity_start_date: params.start_date,
          activity_end_date: params.end_date,
        };
        const dailyMessagesData =
          await userAnalyticsApi.getUserDailyMessages(params);
        setUserInfo(dailyMessagesData);
        setAllUsersConversationPage(null);
        setAllUsersConversationQuery(conversationQuery);
        setTodayStats(null);
        setSessions([]);
        setSessionMessages({});
        setExpandedSessions(new Set());

        setLoadingAllUsersConversations(true);
        void loadAllUsersConversationPage(1, conversationQuery)
          .catch((error: unknown) => {
            console.error("加载分页聊天详情失败:", error);
            message.error(getErrorMessage(error, "加载分页聊天详情失败"));
          })
          .finally(() => {
            setLoadingAllUsersConversations(false);
          });
      }

      message.success("查询成功");
    } catch (error: unknown) {
      console.error("查询失败:", error);
      message.error(getErrorMessage(error, "查询失败"));
      setUserInfo(null);
      setTodayStats(null);
      setAllUsersConversationPage(null);
      setAllUsersConversationQuery(null);
    } finally {
      setLoading(false);
    }
  }, [searchType, searchValue, dateRange, loadAllUsersConversationPage]);

  useEffect(() => {
    if (!deepLinkedUserId) {
      return;
    }
    setSearchType("user_id");
    setSearchValue(deepLinkedUserId);
  }, [deepLinkedUserId]);

  useEffect(() => {
    if (!deepLinkedUserId || hasTriggeredDeepLinkSearchRef.current) {
      return;
    }
    if (searchType !== "user_id" || searchValue.trim() !== deepLinkedUserId) {
      return;
    }
    hasTriggeredDeepLinkSearchRef.current = true;
    handleSearch();
  }, [deepLinkedUserId, searchType, searchValue, handleSearch]);

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
    } catch (error: unknown) {
      console.error("加载会话列表失败:", error);
      message.error(getErrorMessage(error, "加载会话列表失败"));
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
      } catch (error: unknown) {
        console.error("加载会话消息失败:", error);
        message.error(getErrorMessage(error, "加载会话消息失败"));
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

  const handleAllUsersPageChange = useCallback(
    async (page: number) => {
      if (!allUsersConversationQuery) {
        return;
      }
      setLoadingAllUsersConversations(true);
      try {
        await loadAllUsersConversationPage(page, allUsersConversationQuery);
      } catch (error: unknown) {
        console.error("加载分页聊天详情失败:", error);
        message.error(getErrorMessage(error, "加载分页聊天详情失败"));
      } finally {
        setLoadingAllUsersConversations(false);
      }
    },
    [allUsersConversationQuery, loadAllUsersConversationPage],
  );

  // 加载用户生成图片
  const loadUserGeneratedImages = useCallback(async () => {
    const trimmed = searchValue.trim();
    if (!trimmed) {
      return;
    }

    setLoadingUserImages(true);
    try {
      const identifierParams =
        searchType === "email" ? { email: trimmed } : { user_id: trimmed };
      const data = await userAnalyticsApi.getUserGeneratedImages({
        ...identifierParams,
        skip: 0,
        limit: 200,
      });
      setUserImages(data.images);
      setUserImagesTotal(data.total);
    } catch (error: unknown) {
      console.error("加载用户生成图片失败:", error);
      message.error(getErrorMessage(error, "加载用户生成图片失败"));
      setUserImages([]);
      setUserImagesTotal(0);
    } finally {
      setLoadingUserImages(false);
    }
  }, [searchType, searchValue]);

  // 处理点击生图数卡片
  const openCharacterDetail = useCallback(async (agentId: string) => {
    setCharacterDetailOpen(true);
    setCharacterDetailAgent(null);
    setCharacterDetailLoading(true);
    const agent = await agentApi.get(agentId);
    setCharacterDetailAgent(agent);
    setCharacterDetailLoading(false);
  }, []);

  const handleImageCountClick = useCallback(() => {
    if (!todayStats || todayStats.total_generated_images === 0) {
      message.info("该用户暂无生成图片");
      return;
    }
    setShowImagesModal(true);
    loadUserGeneratedImages();
  }, [todayStats, loadUserGeneratedImages]);

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

        // 生成文件名（处理特殊字符）
        const sanitizeFileName = (name: string) => {
          return name.replace(/[<>:"/\\|?*]/g, "_");
        };

        const timestamp = getCurrentUtcTime();
        const safeAgentName = sanitizeFileName(agentName);
        const safeChatId = chatId.substring(0, 20); // 限制长度
        const filename = `session_${safeAgentName}_${safeChatId}_${timestamp}.txt`;

        // 创建并下载文件
        const content = buildSessionExportContent({
          chatId,
          agentName,
          session,
          messages: allMessages,
        });
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
      } catch (error: unknown) {
        console.error("导出会话记录失败:", error);
        message.error(getErrorMessage(error, "导出失败，请重试"));
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
      width: 320,
      render: (_text: string, record: UserSessionItem) => (
        <div>
          <div>{record.agent_name}</div>
          <div style={{ marginTop: 4 }}>
            <Text type="secondary" style={{ fontSize: 12, marginRight: 6 }}>
              ID:
            </Text>
            <Button
              type="link"
              size="small"
              icon={<IdcardOutlined />}
              style={{ padding: 0, height: "auto", fontSize: 12 }}
              onClick={(e) => {
                e.stopPropagation();
                void openCharacterDetail(record.agent_id);
              }}
            >
              {record.agent_id}
            </Button>
          </div>
        </div>
      ),
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
      render: (_value: unknown, record: UserSessionItem) => (
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

  const renderConversationMessages = (
    sessions: UserAgentConversationItem["sessions"],
  ) => {
    if (sessions.length === 0) {
      return <Text type="secondary">暂无会话</Text>;
    }

    return (
      <div style={{ maxHeight: 360, overflowY: "auto" }}>
        {sessions.map((session) => (
          <div key={session.chat_id} style={{ marginBottom: 16 }}>
            <Text strong>
              会话 {session.chat_id}（{session.messages.length} 条）
            </Text>
            <div style={{ marginTop: 8 }}>
              {session.messages.length === 0 ? (
                <Text type="secondary">该会话在查询范围内暂无消息</Text>
              ) : (
                session.messages.map(
                  (msg: ChatMessageResponse, index: number) => {
                    const isUserMessage = isUserMessageType(msg.message_type);
                    return (
                      <div
                        key={`${session.chat_id}-${msg.created_at ?? "no-time"}-${index}`}
                        style={{ marginBottom: 10 }}
                      >
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {isUserMessage ? "👤 用户" : "🤖 AI"} ·{" "}
                          {msg.created_at
                            ? formatUtcTimeRaw(msg.created_at)
                            : "N/A"}
                        </Text>
                        <div>
                          <CollapsibleMessageContent
                            content={msg.content ?? ""}
                          />
                        </div>
                      </div>
                    );
                  },
                )
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const allUsersMessagesColumns: ColumnsType<UserAgentConversationItem> = [
    {
      title: "用户:角色",
      key: "user_agent",
      width: 280,
      render: (_value: unknown, record: UserAgentConversationItem) =>
        `${record.user_id}:${record.agent_id}`,
    },
    {
      title: "用户",
      key: "user",
      width: 220,
      render: (_value: unknown, record: UserAgentConversationItem) => (
        <div>
          <div>{record.nickname || "未设置昵称"}</div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.email || record.user_id}
          </Text>
        </div>
      ),
    },
    {
      title: "角色",
      dataIndex: "agent_name",
      key: "agent_name",
      width: 160,
    },
    {
      title: "会话数",
      dataIndex: "session_count",
      key: "session_count",
      width: 100,
    },
    {
      title: "消息数",
      dataIndex: "message_count",
      key: "message_count",
      width: 100,
    },
    {
      title: "聊天信息（查询范围内）",
      key: "messages",
      width: 720,
      render: (_value: unknown, record: UserAgentConversationItem) =>
        renderConversationMessages(record.sessions),
    },
  ];

  // 计算总消息数
  const totalMessages =
    userInfo?.daily_messages.reduce(
      (sum, item) => sum + item.message_count,
      0,
    ) || 0;
  const isAllUsersResult = userInfo?.user_id === "ALL_USERS";
  const allUsersSessionCount = useMemo(
    () =>
      countUserAgentConversationSessions(allUsersConversationPage?.items || []),
    [allUsersConversationPage],
  );
  const allUsersMessageCount = useMemo(
    () =>
      countUserAgentConversationMessages(allUsersConversationPage?.items || []),
    [allUsersConversationPage],
  );

  const visibleSessions = useMemo(
    () => filterSessionsWithMessages(sessions),
    [sessions],
  );

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
            <span>查询值（可选）：</span>
            <Input
              placeholder={
                searchType === "email"
                  ? "请输入用户邮箱（可留空）"
                  : "请输入用户ID（可留空）"
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
            {userInfo && !isAllUsersResult && (
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
          {!isAllUsersResult && (
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
                      color={
                        userInfo.auth_type === "GOOGLE" ? "blue" : "orange"
                      }
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
                      <span style={{ color: "rgba(0, 0, 0, 0.25)" }}>
                        未设置
                      </span>
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
          )}

          {/* 当日统计卡片 */}
          {!isAllUsersResult && todayStats && (
            <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
              <Col xs={24} sm={12} md={6}>
                <Card>
                  <Statistic
                    title="今日消息数"
                    value={todayStats.today_message_count}
                    prefix={<MessageOutlined />}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card>
                  <Statistic
                    title="今日会话数"
                    value={todayStats.today_session_count}
                    prefix={<MessageOutlined />}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card>
                  <Statistic
                    title="总消息数"
                    value={totalMessages}
                    prefix={<MessageOutlined />}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card
                  style={{
                    cursor:
                      todayStats.total_generated_images > 0
                        ? "pointer"
                        : "default",
                  }}
                  onClick={handleImageCountClick}
                  hoverable={todayStats.total_generated_images > 0}
                >
                  <Statistic
                    title="用户总的生图数"
                    value={todayStats.total_generated_images || 0}
                    prefix={<PictureOutlined />}
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

          {isAllUsersResult && (
            <Card
              title="按 user_id:agent_id 分组的聊天明细（按日期范围）"
              style={{ marginBottom: "24px" }}
              extra={
                <Space size="middle">
                  <Text type="secondary">
                    分组总数：{allUsersConversationPage?.total ?? 0}
                  </Text>
                  <Text type="secondary">
                    当前页会话数：{allUsersSessionCount}
                  </Text>
                  <Text type="secondary">
                    当前页消息数：{allUsersMessageCount}
                  </Text>
                </Space>
              }
            >
              {(allUsersConversationPage?.items.length ?? 0) > 0 ? (
                <Table
                  columns={allUsersMessagesColumns}
                  dataSource={allUsersConversationPage?.items ?? []}
                  rowKey={(record) => `${record.user_id}:${record.agent_id}`}
                  loading={loadingAllUsersConversations}
                  pagination={{
                    current: allUsersConversationPage?.page ?? 1,
                    pageSize: 10,
                    total: allUsersConversationPage?.total ?? 0,
                    showSizeChanger: false,
                    showTotal: (total) => `共 ${total} 组 user_id:agent_id`,
                    onChange: (page) => {
                      handleAllUsersPageChange(page);
                    },
                  }}
                  scroll={{ x: 1700 }}
                />
              ) : (
                <Empty description="该日期范围内暂无 user_id:agent_id 聊天明细" />
              )}
            </Card>
          )}

          {/* 会话列表和对话历史 */}
          {!isAllUsersResult && (
            <Card
              title="会话列表和对话历史"
              style={{ marginBottom: "24px" }}
              extra={
                visibleSessions.length > 0 && (
                  <span style={{ fontSize: "12px", color: "#666" }}>
                    点击行展开查看对话记录
                  </span>
                )
              }
            >
              {visibleSessions.length > 0 ? (
                <Table
                  columns={sessionsColumns}
                  dataSource={visibleSessions}
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
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 8,
                                    flexWrap: "wrap",
                                  }}
                                >
                                  <span>
                                    {msg.message_type === "human" ||
                                    msg.message_type === "HumanMessage"
                                      ? "👤 用户"
                                      : "🤖 AI"}{" "}
                                    •{" "}
                                    {msg.created_at
                                      ? formatUtcTimeRaw(msg.created_at)
                                      : ""}
                                  </span>
                                  {(msg.message_type === "ai" ||
                                    msg.message_type === "AIMessage") &&
                                    msg.meta_data?.langsmith_trace_id && (
                                      <a
                                        href={
                                          getLangsmithTraceUrl(
                                            msg.meta_data.langsmith_trace_id,
                                          )!
                                        }
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        style={{
                                          fontSize: 11,
                                          color: "#1890ff",
                                        }}
                                        title="View LangSmith trace"
                                      >
                                        LangSmith trace
                                      </a>
                                    )}
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
                                  <div style={{ marginTop: 8 }}>
                                    <div style={{ marginBottom: 6 }}>
                                      <Tag color="purple">Voice message</Tag>
                                      <a
                                        href={msg.audio_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        title="Open recording in new tab"
                                        style={{
                                          marginLeft: 8,
                                          fontSize: 12,
                                        }}
                                      >
                                        Open recording
                                      </a>
                                    </div>
                                    <audio
                                      src={msg.audio_url}
                                      controls
                                      preload="metadata"
                                      style={{
                                        width: "100%",
                                        maxWidth: 320,
                                        height: 32,
                                      }}
                                    />
                                    <div
                                      style={{
                                        marginTop: 6,
                                        fontSize: 11,
                                        fontFamily: "monospace",
                                        color: "#666",
                                        wordBreak: "break-all",
                                      }}
                                      title={msg.audio_url}
                                    >
                                      GCS: {msg.audio_url}
                                    </div>
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
                                          {msg.meta_data.generated_image.width}{" "}
                                          ×{" "}
                                          {msg.meta_data.generated_image.height}
                                        </div>
                                      )}
                                  </div>
                                )}
                              </div>
                            ),
                          )}
                          {shouldShowSessionMessagesPagination(
                            messagesData,
                          ) && (
                            <div style={{ textAlign: "center", marginTop: 16 }}>
                              <Pagination
                                current={messagesData.page}
                                total={messagesData.total}
                                pageSize={messagesData.size}
                                showTotal={(total) => `共 ${total} 条消息`}
                                onChange={(page) =>
                                  handleMessagePageChange(record.chat_id, page)
                                }
                                {...sessionMessagesPaginationProps}
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
                      : sessions.length > 0 && visibleSessions.length === 0
                        ? "暂无有聊天记录的会话（消息数为 0 的不展示）"
                        : "暂无会话数据，会话列表会在查询用户信息后自动加载"
                  }
                />
              )}
            </Card>
          )}
        </>
      )}

      {!userInfo && !loading && (
        <Card>
          <Empty description="请输入用户邮箱或用户ID，或仅选择日期范围后点击查询" />
        </Card>
      )}

      {/* 用户生成图片展示 Modal */}
      <Modal
        open={showImagesModal}
        onCancel={() => {
          setShowImagesModal(false);
          setUserImages([]);
          setUserImagesTotal(0);
        }}
        footer={null}
        width={1200}
        title={
          <Space>
            <PictureOutlined />
            <span>用户生成图片</span>
            <Tag color="green">{userImagesTotal} 张</Tag>
          </Space>
        }
      >
        {loadingUserImages ? (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              minHeight: "400px",
            }}
          >
            <Spin size="large" />
          </div>
        ) : userImages.length === 0 ? (
          <Empty description="该用户暂无生成图片" style={{ marginTop: 100 }} />
        ) : (
          <div>
            <Row
              gutter={[16, 16]}
              style={{ maxHeight: "70vh", overflow: "auto" }}
            >
              {userImages.map((image, index) => (
                <Col key={index} xs={12} sm={8} md={6} lg={4} xl={3}>
                  <Card
                    hoverable
                    size="small"
                    cover={
                      <div
                        style={{
                          position: "relative",
                          paddingTop: "100%",
                          overflow: "hidden",
                        }}
                      >
                        <img
                          src={image.url}
                          alt={`生成图片 ${index + 1}`}
                          style={{
                            position: "absolute",
                            top: 0,
                            left: 0,
                            width: "100%",
                            height: "100%",
                            objectFit: "cover",
                            cursor: "pointer",
                          }}
                          onClick={() => setPreviewImage(image)}
                          onError={(e) => {
                            const imgElement = e.target as HTMLImageElement;
                            console.error("图片加载失败:", {
                              cdnUrl: image.url,
                              gcsUrl: image.gcs_url,
                              error: e,
                            });
                            // 如果CDN URL加载失败，尝试使用GCS URL
                            if (
                              image.gcs_url &&
                              imgElement.src !== image.gcs_url
                            ) {
                              imgElement.src = image.gcs_url;
                            } else {
                              // 如果GCS URL也失败，显示占位图
                              imgElement.src =
                                "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect width='100' height='100' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23999' font-size='12'%3E图片加载失败%3C/text%3E%3C/svg%3E";
                            }
                          }}
                        />
                      </div>
                    }
                    bodyStyle={{ padding: "8px" }}
                  >
                    <Tooltip title={image.generation_prompt}>
                      <Paragraph
                        ellipsis={{ rows: 2 }}
                        style={{ fontSize: 12, marginBottom: 4 }}
                      >
                        {image.generation_prompt}
                      </Paragraph>
                    </Tooltip>
                    {image.agent_name && (
                      <div style={{ marginBottom: 4 }}>
                        <Tag color="blue" style={{ fontSize: 10 }}>
                          {image.agent_name}
                        </Tag>
                      </div>
                    )}
                    {image.width && image.height && (
                      <Text
                        type="secondary"
                        style={{ fontSize: 10, display: "block" }}
                      >
                        尺寸: {image.width} × {image.height}
                      </Text>
                    )}
                    {image.created_at && (
                      <Text
                        type="secondary"
                        style={{ fontSize: 10, display: "block" }}
                      >
                        {formatUtcTimeRaw(image.created_at)}
                      </Text>
                    )}
                  </Card>
                </Col>
              ))}
            </Row>
          </div>
        )}
      </Modal>

      {/* 图片预览 Modal */}
      <Modal
        open={!!previewImage}
        onCancel={() => setPreviewImage(null)}
        footer={null}
        width={900}
        centered
        title={
          previewImage ? (
            <Space>
              <PictureOutlined />
              <span>图片预览</span>
              {previewImage.agent_name && (
                <Tag color="blue">{previewImage.agent_name}</Tag>
              )}
            </Space>
          ) : null
        }
      >
        {previewImage && (
          <div>
            <div style={{ textAlign: "center", marginBottom: 16 }}>
              <img
                src={previewImage.url}
                alt="预览图片"
                style={{
                  maxWidth: "100%",
                  maxHeight: "600px",
                  borderRadius: 8,
                }}
                onError={(e) => {
                  const imgElement = e.target as HTMLImageElement;
                  if (
                    previewImage.gcs_url &&
                    imgElement.src !== previewImage.gcs_url
                  ) {
                    imgElement.src = previewImage.gcs_url;
                  }
                }}
              />
            </div>
            <div style={{ marginTop: 16 }}>
              <Text strong>生成提示词：</Text>
              <Paragraph style={{ marginTop: 8 }}>
                {previewImage.generation_prompt}
              </Paragraph>
              {previewImage.width && previewImage.height && (
                <div style={{ marginTop: 8 }}>
                  <Text strong>尺寸：</Text>{" "}
                  <Text>
                    {previewImage.width} × {previewImage.height}
                  </Text>
                </div>
              )}
              {previewImage.created_at && (
                <div style={{ marginTop: 8 }}>
                  <Text strong>生成时间：</Text>{" "}
                  <Text>{formatUtcTimeRaw(previewImage.created_at)}</Text>
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>

      <AgentDetailModal
        open={characterDetailOpen}
        agent={characterDetailAgent}
        loading={characterDetailLoading}
        onClose={() => {
          setCharacterDetailOpen(false);
          setCharacterDetailAgent(null);
        }}
        width={800}
      />
    </div>
  );
};
