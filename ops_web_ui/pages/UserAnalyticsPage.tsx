/**
 * 用户数据分析页面
 * 展示用户注册和聊天行为数据，包括图表和详细对话内容
 */

import React, { useState, useEffect, useCallback } from "react";
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
  Collapse,
  message,
  Spin,
  Empty,
} from "antd";
import {
  ReloadOutlined,
  SearchOutlined,
  UserOutlined,
  MessageOutlined,
  PictureOutlined,
  PhoneOutlined,
} from "@ant-design/icons";
import Plot from "react-plotly.js";
import type { ColumnsType } from "antd/es/table";
import type { Dayjs } from "dayjs";
import { userAnalyticsApi } from "../services/api";
import { formatUtcTimeOnly } from "../utils/dateUtils";
import type {
  DailyNewUsers,
  ConversationRoundsResponse,
  UserRoundsDistributionItem,
  PopularAgentsResponse,
  UsersHittingLimitResponse,
  UserSessionsDetailResponse,
  ConversationsDetailResponse,
  UserAnalyticsStatsResponse,
} from "../types";

const { RangePicker } = DatePicker;
const { Option } = Select;

interface AnalyticsDateParams {
  // 注册日期范围
  register_start_date?: string;
  register_end_date?: string;
  register_last_days?: number;
  // 活跃日期范围
  activity_start_date?: string;
  activity_end_date?: string;
  activity_last_days?: number;
}

export const UserAnalyticsPage: React.FC = () => {
  // 用户注册日期范围状态
  const [registerDateType, setRegisterDateType] = useState<
    "all" | "range" | "last_days"
  >("last_days");
  const [registerLastDays, setRegisterLastDays] = useState<number>(7);
  const [registerCustomRange, setRegisterCustomRange] = useState<
    [Dayjs, Dayjs] | null
  >(null);

  // 用户活跃日期范围状态
  const [activityDateType, setActivityDateType] = useState<
    "all" | "range" | "last_days"
  >("last_days");
  const [activityLastDays, setActivityLastDays] = useState<number>(7);
  const [activityCustomRange, setActivityCustomRange] = useState<
    [Dayjs, Dayjs] | null
  >(null);

  // 数据加载状态
  const [loading, setLoading] = useState(false);

  // 数据状态
  const [newUsers, setNewUsers] = useState<DailyNewUsers[]>([]);
  const [conversationRounds, setConversationRounds] = useState<
    ConversationRoundsResponse[]
  >([]);
  const [userRoundsDistribution, setUserRoundsDistribution] = useState<
    UserRoundsDistributionItem[]
  >([]);
  const [popularAgents, setPopularAgents] = useState<PopularAgentsResponse[]>(
    [],
  );
  const [usersHittingLimit, setUsersHittingLimit] = useState<
    UsersHittingLimitResponse[]
  >([]);
  const [userSessionsDetail, setUserSessionsDetail] = useState<
    UserSessionsDetailResponse[]
  >([]);
  const [conversationsDetail, setConversationsDetail] = useState<
    ConversationsDetailResponse[]
  >([]);
  const [stats, setStats] = useState<UserAnalyticsStatsResponse | null>(null);

  // 对话详情查看器状态
  const [showConversationsDetail, setShowConversationsDetail] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState("");
  const [authTypeFilter, setAuthTypeFilter] = useState<
    "all" | "GUEST" | "GOOGLE"
  >("all");
  const [sessionTypeFilter, setSessionTypeFilter] = useState<
    "all" | "with_messages" | "opening_only"
  >("all");

  // 获取日期范围参数
  const getDateRangeParams = useCallback((): AnalyticsDateParams => {
    const params: AnalyticsDateParams = {};

    // 注册日期范围
    // "all" 时不传递参数，后端会使用默认的全部数据范围
    if (registerDateType === "last_days") {
      params.register_last_days = registerLastDays;
    } else if (
      registerDateType === "range" &&
      registerCustomRange &&
      registerCustomRange[0] &&
      registerCustomRange[1]
    ) {
      params.register_start_date = registerCustomRange[0].format("YYYY-MM-DD");
      params.register_end_date = registerCustomRange[1].format("YYYY-MM-DD");
    }
    // registerDateType === "all" 时不传递任何注册日期参数

    // 活跃日期范围
    // "all" 时不传递参数，后端会使用默认的全部数据范围
    if (activityDateType === "last_days") {
      params.activity_last_days = activityLastDays;
    } else if (
      activityDateType === "range" &&
      activityCustomRange &&
      activityCustomRange[0] &&
      activityCustomRange[1]
    ) {
      params.activity_start_date = activityCustomRange[0].format("YYYY-MM-DD");
      params.activity_end_date = activityCustomRange[1].format("YYYY-MM-DD");
    } else if (activityDateType !== "all") {
      // 活跃范围为空时（非"全部"），使用注册范围的值
      if (params.register_last_days) {
        params.activity_last_days = params.register_last_days;
      } else if (params.register_start_date && params.register_end_date) {
        params.activity_start_date = params.register_start_date;
        params.activity_end_date = params.register_end_date;
      }
    }
    // activityDateType === "all" 时不传递任何活跃日期参数

    return params;
  }, [
    registerDateType,
    registerLastDays,
    registerCustomRange,
    activityDateType,
    activityLastDays,
    activityCustomRange,
  ]);

  // 加载所有数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params = getDateRangeParams();
      // 注册日期范围现在支持"全部"选项，不再强制校验

      const [
        statsData,
        newUsersData,
        conversationRoundsData,
        userRoundsDistributionData,
        popularAgentsData,
        usersHittingLimitData,
        userSessionsDetailData,
      ] = await Promise.all([
        userAnalyticsApi.getStats(params),
        userAnalyticsApi.getNewUsers(params),
        userAnalyticsApi.getConversationRounds(params),
        userAnalyticsApi.getUserRoundsDistribution(params),
        userAnalyticsApi.getPopularAgents(params),
        userAnalyticsApi.getUsersHittingLimit(params),
        userAnalyticsApi.getUserSessionsDetail(params),
      ]);

      setStats(statsData);
      setNewUsers(newUsersData);
      setConversationRounds(conversationRoundsData);
      setUserRoundsDistribution(userRoundsDistributionData);
      setPopularAgents(popularAgentsData);
      setUsersHittingLimit(usersHittingLimitData);
      setUserSessionsDetail(userSessionsDetailData);

      message.success("数据加载成功");
    } catch (error) {
      console.error("加载数据失败:", error);
      message.error("加载数据失败");
    } finally {
      setLoading(false);
    }
  }, [getDateRangeParams]);

  // 加载对话详情
  const loadConversationsDetail = useCallback(async () => {
    setLoading(true);
    try {
      const params = getDateRangeParams();
      const data = await userAnalyticsApi.getConversationsDetail(params);
      setConversationsDetail(data);
      message.success("对话详情加载成功");
    } catch (error) {
      console.error("加载对话详情失败:", error);
      message.error("加载对话详情失败");
    } finally {
      setLoading(false);
    }
  }, [getDateRangeParams]);

  // 初始化加载
  useEffect(() => {
    loadData();
  }, [loadData]);

  // 统计数据从后端API获取，不再在前端计算

  // 处理轮数分布（按Session）- 与原始脚本逻辑一致
  // bins: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, inf]
  // labels: ["1-10", "11-20", "21-30", ..., "91-100", "100+"]
  // pd.cut(..., right=True): 区间是 (a, b]（左开右闭），但第一个区间包含最小值
  // 所以：[0, 10] -> "1-10", (10, 20] -> "11-20", (20, 30] -> "21-30", ...
  const roundsDistributionBySession = React.useMemo(() => {
    const buckets: Record<string, number> = {};
    const labels = [
      "1-10",
      "11-20",
      "21-30",
      "31-40",
      "41-50",
      "51-60",
      "61-70",
      "71-80",
      "81-90",
      "91-100",
      "100+",
    ];

    conversationRounds.forEach((item) => {
      const rounds = item.message_count_excluding_opening;
      let bucketKey: string;

      // 按照 pd.cut(..., right=True) 的逻辑
      // 第一个区间 [0, 10]：包含 0 和 10
      // 其他区间 (a, b]：不包含 a，包含 b
      if (rounds >= 0 && rounds <= 10) {
        bucketKey = "1-10"; // [0, 10]
      } else if (rounds > 10 && rounds <= 20) {
        bucketKey = "11-20"; // (10, 20]
      } else if (rounds > 20 && rounds <= 30) {
        bucketKey = "21-30"; // (20, 30]
      } else if (rounds > 30 && rounds <= 40) {
        bucketKey = "31-40"; // (30, 40]
      } else if (rounds > 40 && rounds <= 50) {
        bucketKey = "41-50"; // (40, 50]
      } else if (rounds > 50 && rounds <= 60) {
        bucketKey = "51-60"; // (50, 60]
      } else if (rounds > 60 && rounds <= 70) {
        bucketKey = "61-70"; // (60, 70]
      } else if (rounds > 70 && rounds <= 80) {
        bucketKey = "71-80"; // (70, 80]
      } else if (rounds > 80 && rounds <= 90) {
        bucketKey = "81-90"; // (80, 90]
      } else if (rounds > 90 && rounds <= 100) {
        bucketKey = "91-100"; // (90, 100]
      } else if (rounds > 100) {
        bucketKey = "100+"; // (100, inf)
      } else {
        // 负数或无效值，跳过
        return;
      }

      buckets[bucketKey] = (buckets[bucketKey] || 0) + 1;
    });

    // 确保所有区间都存在（即使为0）
    const result = labels.map((label) => ({
      rounds_range: label,
      count: buckets[label] || 0,
    }));

    return result;
  }, [conversationRounds]);

  // 处理轮数分布（按用户）- 与原始脚本逻辑一致
  // bins: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, inf]
  // labels: ["1-10", "11-20", "21-30", ..., "91-100", "100+"]
  // pd.cut(..., right=True): 区间是 (a, b]（左开右闭），但第一个区间包含最小值
  // 只统计有对话的用户（total_rounds > 0）
  const roundsDistributionByUser = React.useMemo(() => {
    const buckets: Record<string, number> = {};
    const labels = [
      "1-10",
      "11-20",
      "21-30",
      "31-40",
      "41-50",
      "51-60",
      "61-70",
      "71-80",
      "81-90",
      "91-100",
      "100+",
    ];

    userRoundsDistribution.forEach((item) => {
      const rounds = item.total_rounds;
      // 只统计有对话的用户（与原始脚本一致）
      if (rounds <= 0) {
        return;
      }

      let bucketKey: string;
      // 按照 pd.cut(..., right=True) 的逻辑
      // 第一个区间 [0, 10]：包含 0 和 10
      // 其他区间 (a, b]：不包含 a，包含 b
      if (rounds >= 0 && rounds <= 10) {
        bucketKey = "1-10"; // [0, 10]
      } else if (rounds > 10 && rounds <= 20) {
        bucketKey = "11-20"; // (10, 20]
      } else if (rounds > 20 && rounds <= 30) {
        bucketKey = "21-30"; // (20, 30]
      } else if (rounds > 30 && rounds <= 40) {
        bucketKey = "31-40"; // (30, 40]
      } else if (rounds > 40 && rounds <= 50) {
        bucketKey = "41-50"; // (40, 50]
      } else if (rounds > 50 && rounds <= 60) {
        bucketKey = "51-60"; // (50, 60]
      } else if (rounds > 60 && rounds <= 70) {
        bucketKey = "61-70"; // (60, 70]
      } else if (rounds > 70 && rounds <= 80) {
        bucketKey = "71-80"; // (70, 80]
      } else if (rounds > 80 && rounds <= 90) {
        bucketKey = "81-90"; // (80, 90]
      } else if (rounds > 90 && rounds <= 100) {
        bucketKey = "91-100"; // (90, 100]
      } else if (rounds > 100) {
        bucketKey = "100+"; // (100, inf)
      } else {
        // 负数或无效值，跳过
        return;
      }

      buckets[bucketKey] = (buckets[bucketKey] || 0) + 1;
    });

    // 确保所有区间都存在（即使为0）
    const result = labels.map((label) => ({
      rounds_range: label,
      user_count: buckets[label] || 0,
    }));

    return result;
  }, [userRoundsDistribution]);

  // 处理达到限制的用户趋势
  const usersHittingLimitTrend = React.useMemo(() => {
    const dailyData: Record<string, { GUEST: number; GOOGLE: number }> = {};
    usersHittingLimit.forEach((item) => {
      if (!dailyData[item.date]) {
        dailyData[item.date] = { GUEST: 0, GOOGLE: 0 };
      }
      dailyData[item.date][item.auth_type as "GUEST" | "GOOGLE"] += 1;
    });
    return Object.entries(dailyData)
      .map(([date, counts]) => ({
        date,
        GUEST: counts.GUEST,
        GOOGLE: counts.GOOGLE,
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [usersHittingLimit]);

  // 过滤对话详情
  const filteredConversationsDetail = React.useMemo(() => {
    let filtered = conversationsDetail;

    // 按认证类型过滤
    if (authTypeFilter !== "all") {
      filtered = filtered.filter((item) => item.auth_type === authTypeFilter);
    }

    // 按会话类型过滤
    if (sessionTypeFilter === "with_messages") {
      filtered = filtered.filter((item) =>
        item.sessions.some((s) => s.message_count > 0),
      );
    } else if (sessionTypeFilter === "opening_only") {
      filtered = filtered.filter((item) =>
        item.sessions.every((s) => s.message_count === 0),
      );
    }

    // 按关键词搜索
    if (searchKeyword) {
      const keyword = searchKeyword.toLowerCase();
      filtered = filtered.filter(
        (item) =>
          item.user_id.toLowerCase().includes(keyword) ||
          item.nickname?.toLowerCase().includes(keyword) ||
          item.email?.toLowerCase().includes(keyword) ||
          item.sessions.some((s) =>
            s.agent_name.toLowerCase().includes(keyword),
          ),
      );
    }

    // 按消息数降序排序
    return filtered.sort((a, b) => {
      const aTotal = a.sessions.reduce((sum, s) => sum + s.message_count, 0);
      const bTotal = b.sessions.reduce((sum, s) => sum + s.message_count, 0);
      return bTotal - aTotal;
    });
  }, [conversationsDetail, authTypeFilter, sessionTypeFilter, searchKeyword]);

  // 表格列定义
  const columns: ColumnsType<UserSessionsDetailResponse> = [
    {
      title: "用户ID",
      dataIndex: "user_id",
      key: "user_id",
      width: 320,
      render: (userId: string) => (
        <span style={{ fontFamily: "monospace", wordBreak: "break-all" }}>
          {userId}
        </span>
      ),
    },
    {
      title: "认证类型",
      dataIndex: "auth_type",
      key: "auth_type",
      width: 100,
      render: (auth_type: string) => (
        <Tag color={auth_type === "GOOGLE" ? "blue" : "orange"}>
          {auth_type}
        </Tag>
      ),
    },
    {
      title: "注册时间",
      dataIndex: "user_created_at",
      key: "user_created_at",
      width: 180,
    },
    {
      title: "角色名称",
      dataIndex: "agent_name",
      key: "agent_name",
      width: 150,
    },
    {
      title: "消息数",
      dataIndex: "message_count",
      key: "message_count",
      width: 100,
      sorter: (a, b) => a.message_count - b.message_count,
    },
    {
      title: "语音消息数",
      dataIndex: "voice_message_count",
      key: "voice_message_count",
      width: 120,
      sorter: (a, b) => a.voice_message_count - b.voice_message_count,
    },
  ];

  return (
    <div style={{ padding: "24px" }}>
      {/* 日期选择器 */}
      <Card style={{ marginBottom: "24px" }}>
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          {/* 用户注册日期范围 */}
          <Space wrap>
            <span style={{ fontWeight: 500 }}>用户注册范围：</span>
            <Select
              value={registerDateType}
              onChange={setRegisterDateType}
              style={{ width: 120 }}
            >
              <Option value="all">全部</Option>
              <Option value="last_days">最近N天</Option>
              <Option value="range">自定义范围</Option>
            </Select>
            {registerDateType === "last_days" && (
              <Select
                value={registerLastDays}
                onChange={setRegisterLastDays}
                style={{ width: 120 }}
              >
                <Option value={1}>最近1天</Option>
                <Option value={3}>最近3天</Option>
                <Option value={7}>最近7天</Option>
                <Option value={14}>最近14天</Option>
                <Option value={30}>最近30天</Option>
                <Option value={90}>最近90天</Option>
              </Select>
            )}
            {registerDateType === "range" && (
              <RangePicker
                value={registerCustomRange}
                onChange={(dates) =>
                  setRegisterCustomRange(dates as [Dayjs, Dayjs] | null)
                }
                format="YYYY-MM-DD"
              />
            )}
          </Space>

          {/* 用户活跃日期范围 */}
          <Space wrap>
            <span style={{ fontWeight: 500 }}>用户活跃范围：</span>
            <Select
              value={activityDateType}
              onChange={setActivityDateType}
              style={{ width: 120 }}
            >
              <Option value="all">全部</Option>
              <Option value="last_days">最近N天</Option>
              <Option value="range">自定义范围</Option>
            </Select>
            {activityDateType === "last_days" && (
              <Select
                value={activityLastDays}
                onChange={setActivityLastDays}
                style={{ width: 120 }}
              >
                <Option value={1}>最近1天</Option>
                <Option value={3}>最近3天</Option>
                <Option value={7}>最近7天</Option>
                <Option value={14}>最近14天</Option>
                <Option value={30}>最近30天</Option>
                <Option value={90}>最近90天</Option>
              </Select>
            )}
            {activityDateType === "range" && (
              <RangePicker
                value={activityCustomRange}
                onChange={(dates) =>
                  setActivityCustomRange(dates as [Dayjs, Dayjs] | null)
                }
                format="YYYY-MM-DD"
              />
            )}
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={loadData}
              loading={loading}
            >
              查询
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadData}>
              刷新
            </Button>
          </Space>
        </Space>
      </Card>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="用户数"
              value={stats?.total_new_users ?? 0}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="发起聊天的人数"
              value={stats?.total_chat_initiators ?? 0}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="包含用户消息的会话数"
              value={stats?.total_active_sessions ?? 0}
              prefix={<MessageOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总发送消息数"
              value={stats?.total_user_messages ?? 0}
              prefix={<MessageOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="人均消息数"
              value={stats?.avg_messages_per_user.toFixed(1) ?? "0.0"}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="人均会话数"
              value={stats?.avg_sessions_per_user.toFixed(1) ?? "0.0"}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="人均语音请求数"
              value={stats?.avg_voice_requests_per_user.toFixed(1) ?? "0.0"}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="每会话平均轮数"
              value={stats?.avg_rounds_per_session.toFixed(1) ?? "0.0"}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="开口率"
              value={stats?.new_user_open_rate.toFixed(2) ?? "0.00"}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* 生图统计 */}
      <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="总生图请求数"
              value={stats?.total_image_generation_requests ?? 0}
              prefix={<PictureOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="生图成功次数"
              value={stats?.total_image_generation_success ?? 0}
              prefix={<PictureOutlined />}
              valueStyle={{ color: "#3f8600" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="生图失败次数"
              value={stats?.total_image_generation_failures ?? 0}
              prefix={<PictureOutlined />}
              valueStyle={{ color: "#cf1322" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="生图成功率"
              value={stats?.image_generation_success_rate.toFixed(2) ?? "0.00"}
              suffix="%"
              prefix={<PictureOutlined />}
              valueStyle={{
                color:
                  (stats?.image_generation_success_rate ?? 0) >= 80
                    ? "#3f8600"
                    : (stats?.image_generation_success_rate ?? 0) >= 50
                      ? "#faad14"
                      : "#cf1322",
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 生图细分统计 */}
      <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="新生成次数"
              value={stats?.total_image_new_generation ?? 0}
              prefix={<PictureOutlined />}
              valueStyle={{ color: "#3f8600" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="兜底图片次数"
              value={stats?.total_image_fallback_used ?? 0}
              prefix={<PictureOutlined />}
              valueStyle={{ color: "#faad14" }}
            />
          </Card>
        </Col>
      </Row>

      {/* 语音通话统计（Live Chat） */}
      <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="发起语音通话人数"
              value={stats?.total_live_chat_users ?? 0}
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="语音通话次数"
              value={stats?.total_live_chat_sessions ?? 0}
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="总通话时长（秒）"
              value={stats?.total_live_chat_duration ?? 0}
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="人均通话次数"
              value={
                stats?.avg_live_chat_sessions_per_user?.toFixed(2) ?? "0.00"
              }
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="人均通话时长（秒）"
              value={
                stats?.avg_live_chat_duration_per_user?.toFixed(2) ?? "0.00"
              }
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card>
            <Statistic
              title="每次平均时长（秒）"
              value={
                stats?.avg_live_chat_duration_per_session?.toFixed(2) ?? "0.00"
              }
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={[16, 16]}>
        {/* 图表1: 用户注册结构 */}
        <Col xs={24} lg={12}>
          <Card title="用户注册结构" style={{ height: "400px" }}>
            {newUsers.length > 0 ? (
              <Plot
                data={[
                  {
                    x: newUsers
                      .filter((d) => d.auth_type === "GUEST")
                      .map((d) => d.date),
                    y: newUsers
                      .filter((d) => d.auth_type === "GUEST")
                      .map((d) => d.count),
                    name: "GUEST 用户",
                    type: "bar",
                  },
                  {
                    x: newUsers
                      .filter((d) => d.auth_type === "GOOGLE")
                      .map((d) => d.date),
                    y: newUsers
                      .filter((d) => d.auth_type === "GOOGLE")
                      .map((d) => d.count),
                    name: "GOOGLE 用户",
                    type: "bar",
                  },
                ]}
                layout={{
                  title: "用户注册结构",
                  barmode: "stack",
                  height: 300,
                  xaxis: { title: "日期" },
                  yaxis: { title: "用户数" },
                }}
                style={{ width: "100%", height: "100%" }}
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>

        {/* 表格: Top 20 热门角色 */}
        <Col xs={24} lg={24}>
          <Card title="Top 20 热门角色">
            {popularAgents.length > 0 ? (
              <Table
                columns={[
                  {
                    title: "角色名称",
                    dataIndex: "agent_name",
                    key: "agent_name",
                    width: 200,
                  },
                  {
                    title: "浏览数",
                    dataIndex: "total_sessions",
                    key: "total_sessions",
                    width: 120,
                    sorter: (a, b) => a.total_sessions - b.total_sessions,
                    render: (value: number) => value,
                  },
                  {
                    title: "真实发起聊天人数",
                    dataIndex: "user_count",
                    key: "user_count",
                    width: 150,
                    sorter: (a, b) => a.user_count - b.user_count,
                    defaultSortOrder: "descend",
                  },
                  {
                    title: "开口率",
                    dataIndex: "open_rate",
                    key: "open_rate",
                    width: 120,
                    sorter: (a, b) => a.open_rate - b.open_rate,
                    render: (value: number) => `${value.toFixed(2)}%`,
                  },
                  {
                    title: "总聊天轮数",
                    dataIndex: "total_rounds",
                    key: "total_rounds",
                    width: 120,
                    sorter: (a, b) => a.total_rounds - b.total_rounds,
                  },
                  {
                    title: "人均聊天轮数",
                    dataIndex: "avg_rounds_per_user",
                    key: "avg_rounds_per_user",
                    width: 130,
                    sorter: (a, b) =>
                      a.avg_rounds_per_user - b.avg_rounds_per_user,
                    render: (value: number) => value.toFixed(2),
                  },
                  {
                    title: ">=5轮会话百分比",
                    dataIndex: "pct_sessions_ge_5",
                    key: "pct_sessions_ge_5",
                    width: 150,
                    sorter: (a, b) => a.pct_sessions_ge_5 - b.pct_sessions_ge_5,
                    render: (value: number) => `${value.toFixed(2)}%`,
                  },
                  {
                    title: ">=10轮会话百分比",
                    dataIndex: "pct_sessions_ge_10",
                    key: "pct_sessions_ge_10",
                    width: 160,
                    sorter: (a, b) =>
                      a.pct_sessions_ge_10 - b.pct_sessions_ge_10,
                    render: (value: number) => `${value.toFixed(2)}%`,
                  },
                ]}
                dataSource={popularAgents}
                rowKey="agent_name"
                loading={loading}
                pagination={false}
                size="small"
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>

        {/* 图表3: 对话轮数分布（按Session） */}
        <Col xs={24} lg={12}>
          <Card title="对话轮数分布（按Session）" style={{ height: "400px" }}>
            {roundsDistributionBySession.length > 0 ? (
              <Plot
                data={[
                  {
                    x: roundsDistributionBySession.map((d) => d.rounds_range),
                    y: roundsDistributionBySession.map((d) => d.count),
                    type: "bar",
                    marker: { color: "lightblue" },
                  },
                ]}
                layout={{
                  title: "对话轮数分布（按Session）",
                  height: 300,
                  xaxis: { title: "消息数区间" },
                  yaxis: { title: "Session数量" },
                }}
                style={{ width: "100%", height: "100%" }}
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>

        {/* 图表4: 对话轮数分布（按用户） */}
        <Col xs={24} lg={12}>
          <Card title="对话轮数分布（按用户）" style={{ height: "400px" }}>
            {roundsDistributionByUser.length > 0 ? (
              <Plot
                data={[
                  {
                    x: roundsDistributionByUser.map((d) => d.rounds_range),
                    y: roundsDistributionByUser.map((d) => d.user_count),
                    type: "bar",
                    marker: { color: "lightcoral" },
                  },
                ]}
                layout={{
                  title: "对话轮数分布（按用户）",
                  height: 300,
                  xaxis: { title: "消息数区间" },
                  yaxis: { title: "用户数量" },
                }}
                style={{ width: "100%", height: "100%" }}
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>

        {/* 图表5: 达到聊天限制的用户趋势 */}
        <Col xs={24} lg={12}>
          <Card title="达到聊天限制的用户趋势" style={{ height: "400px" }}>
            {usersHittingLimitTrend.length > 0 ? (
              <Plot
                data={[
                  {
                    x: usersHittingLimitTrend.map((d) => d.date),
                    y: usersHittingLimitTrend.map((d) => d.GUEST),
                    name: "GUEST 达到限制",
                    type: "bar",
                    marker: { color: "orange" },
                  },
                  {
                    x: usersHittingLimitTrend.map((d) => d.date),
                    y: usersHittingLimitTrend.map((d) => d.GOOGLE),
                    name: "GOOGLE 达到限制",
                    type: "bar",
                    marker: { color: "red" },
                  },
                ]}
                layout={{
                  title: "达到聊天限制的用户趋势",
                  height: 300,
                  barmode: "group",
                  xaxis: { title: "日期" },
                  yaxis: { title: "达到限制的用户数" },
                }}
                style={{ width: "100%", height: "100%" }}
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>
      </Row>

      {/* 用户会话详情表格 */}
      <Card
        title="用户会话详情"
        extra={
          <Button
            type="primary"
            onClick={() => {
              if (!showConversationsDetail) {
                loadConversationsDetail();
              }
              setShowConversationsDetail(!showConversationsDetail);
            }}
          >
            {showConversationsDetail ? "隐藏" : "显示"}对话详情
          </Button>
        }
        style={{ marginTop: "24px" }}
      >
        <Table
          columns={columns}
          dataSource={userSessionsDetail}
          rowKey="chat_id"
          loading={loading}
          pagination={{ pageSize: 50 }}
        />
      </Card>

      {/* 对话详情查看器 */}
      {showConversationsDetail && (
        <Card title="对话详情查看器" style={{ marginTop: "24px" }}>
          {/* 过滤和搜索 */}
          <Space
            direction="vertical"
            style={{ width: "100%", marginBottom: 16 }}
          >
            <Space>
              <span>按认证类型筛选：</span>
              <Button
                type={authTypeFilter === "all" ? "primary" : "default"}
                onClick={() => setAuthTypeFilter("all")}
              >
                全部
              </Button>
              <Button
                type={authTypeFilter === "GUEST" ? "primary" : "default"}
                onClick={() => setAuthTypeFilter("GUEST")}
              >
                游客
              </Button>
              <Button
                type={authTypeFilter === "GOOGLE" ? "primary" : "default"}
                onClick={() => setAuthTypeFilter("GOOGLE")}
              >
                Google
              </Button>
            </Space>
            <Space>
              <span>按会话类型筛选：</span>
              <Button
                type={sessionTypeFilter === "all" ? "primary" : "default"}
                onClick={() => setSessionTypeFilter("all")}
              >
                全部
              </Button>
              <Button
                type={
                  sessionTypeFilter === "with_messages" ? "primary" : "default"
                }
                onClick={() => setSessionTypeFilter("with_messages")}
              >
                有用户消息
              </Button>
              <Button
                type={
                  sessionTypeFilter === "opening_only" ? "primary" : "default"
                }
                onClick={() => setSessionTypeFilter("opening_only")}
              >
                仅浏览开场白
              </Button>
            </Space>
            <Input
              placeholder="搜索用户ID、昵称、邮箱、角色名称..."
              prefix={<SearchOutlined />}
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              style={{ width: 400 }}
            />
          </Space>

          {/* 用户卡片列表 */}
          <Spin spinning={loading}>
            {filteredConversationsDetail.length === 0 ? (
              <Empty description="暂无数据" />
            ) : (
              <Collapse
                items={filteredConversationsDetail.map((user) => ({
                  key: user.user_id,
                  label: (
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <Space>
                        <span style={{ wordBreak: "break-all" }}>
                          <span style={{ fontFamily: "monospace" }}>
                            {user.user_id}
                          </span>
                          {user.nickname && ` (${user.nickname})`}
                        </span>
                        <Tag
                          color={
                            user.auth_type === "GOOGLE" ? "blue" : "orange"
                          }
                        >
                          {user.auth_type}
                        </Tag>
                        {user.email && <span>{user.email}</span>}
                      </Space>
                      <Space>
                        <span>{user.sessions.length} 会话</span>
                        <span>
                          {user.sessions.reduce(
                            (sum, s) => sum + s.message_count,
                            0,
                          )}{" "}
                          消息
                        </span>
                      </Space>
                    </div>
                  ),
                  children: (
                    <div>
                      {user.sessions.map((session, idx) => (
                        <Card
                          key={session.chat_id}
                          size="small"
                          style={{ marginBottom: 16 }}
                          title={
                            <Space>
                              <span>
                                会话 {idx + 1}: {session.agent_name}
                              </span>
                              <Tag>{session.message_count} 条消息</Tag>
                              {session.voice_message_count > 0 && (
                                <Tag color="purple">
                                  {session.voice_message_count} 条语音
                                </Tag>
                              )}
                            </Space>
                          }
                        >
                          {session.messages.length > 0 ? (
                            <div>
                              {session.messages.map((msg, msgIdx) => (
                                <div
                                  key={msgIdx}
                                  style={{
                                    marginBottom: 12,
                                    padding: 8,
                                    backgroundColor:
                                      msg.message_type === "human"
                                        ? "#e6f7ff"
                                        : "#f0f0f0",
                                    borderRadius: 4,
                                    textAlign:
                                      msg.message_type === "human"
                                        ? "right"
                                        : "left",
                                  }}
                                >
                                  <div
                                    style={{
                                      fontSize: 12,
                                      color: "#666",
                                      marginBottom: 4,
                                    }}
                                  >
                                    {msg.message_type === "human"
                                      ? "👤 用户"
                                      : "🤖 AI"}{" "}
                                    •{" "}
                                    {msg.created_at
                                      ? formatUtcTimeOnly(msg.created_at)
                                      : ""}
                                  </div>
                                  <div>
                                    {msg.content && msg.content.length > 500
                                      ? `${msg.content.substring(0, 500)}...`
                                      : msg.content}
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <Empty description="无对话记录" />
                          )}
                        </Card>
                      ))}
                    </div>
                  ),
                }))}
              />
            )}
          </Spin>
        </Card>
      )}
    </div>
  );
};
