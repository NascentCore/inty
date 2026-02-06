/**
 * 用户数据分析日报周报页面
 * 展示全部用户的预计算聚合统计，数据由定时任务预计算，不包含对话详情
 * CREATED_BY_AGENT
 */

import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Card,
  Select,
  Space,
  Row,
  Col,
  Statistic,
  Collapse,
  Table,
  message,
  Spin,
  Empty,
} from "antd";
import {
  ReloadOutlined,
  UserOutlined,
  MessageOutlined,
  PictureOutlined,
  PhoneOutlined,
  SoundOutlined,
} from "@ant-design/icons";
import Plot from "react-plotly.js";
import { userAnalyticsApi } from "../services/api";
import type {
  UserAnalyticsReportItem,
  UserAnalyticsStatsResponse,
  UserAnalyticsReportCharts,
} from "../types";

type ReportType = "daily" | "weekly";

const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  daily: "日报",
  weekly: "周报",
};

const ROUNDS_LABELS = [
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

function computeRoundsDistributionBySession(
  conversationRounds: UserAnalyticsReportCharts["conversation_rounds"],
) {
  const buckets: Record<string, number> = {};
  ROUNDS_LABELS.forEach((l) => (buckets[l] = 0));
  conversationRounds.forEach((item) => {
    const rounds = item.message_count_excluding_opening;
    let bucketKey: string;
    if (rounds >= 0 && rounds <= 10) bucketKey = "1-10";
    else if (rounds > 10 && rounds <= 20) bucketKey = "11-20";
    else if (rounds > 20 && rounds <= 30) bucketKey = "21-30";
    else if (rounds > 30 && rounds <= 40) bucketKey = "31-40";
    else if (rounds > 40 && rounds <= 50) bucketKey = "41-50";
    else if (rounds > 50 && rounds <= 60) bucketKey = "51-60";
    else if (rounds > 60 && rounds <= 70) bucketKey = "61-70";
    else if (rounds > 70 && rounds <= 80) bucketKey = "71-80";
    else if (rounds > 80 && rounds <= 90) bucketKey = "81-90";
    else if (rounds > 90 && rounds <= 100) bucketKey = "91-100";
    else if (rounds > 100) bucketKey = "100+";
    else return;
    buckets[bucketKey] = (buckets[bucketKey] || 0) + 1;
  });
  return ROUNDS_LABELS.map((label) => ({
    rounds_range: label,
    count: buckets[label] || 0,
  }));
}

function computeRoundsDistributionByUser(
  userRoundsDistribution: UserAnalyticsReportCharts["user_rounds_distribution"],
) {
  const buckets: Record<string, number> = {};
  ROUNDS_LABELS.forEach((l) => (buckets[l] = 0));
  userRoundsDistribution.forEach((item) => {
    const rounds = item.total_rounds;
    if (rounds <= 0) return;
    let bucketKey: string;
    if (rounds >= 0 && rounds <= 10) bucketKey = "1-10";
    else if (rounds > 10 && rounds <= 20) bucketKey = "11-20";
    else if (rounds > 20 && rounds <= 30) bucketKey = "21-30";
    else if (rounds > 30 && rounds <= 40) bucketKey = "31-40";
    else if (rounds > 40 && rounds <= 50) bucketKey = "41-50";
    else if (rounds > 50 && rounds <= 60) bucketKey = "51-60";
    else if (rounds > 60 && rounds <= 70) bucketKey = "61-70";
    else if (rounds > 70 && rounds <= 80) bucketKey = "71-80";
    else if (rounds > 80 && rounds <= 90) bucketKey = "81-90";
    else if (rounds > 90 && rounds <= 100) bucketKey = "91-100";
    else if (rounds > 100) bucketKey = "100+";
    else return;
    buckets[bucketKey] = (buckets[bucketKey] || 0) + 1;
  });
  return ROUNDS_LABELS.map((label) => ({
    rounds_range: label,
    user_count: buckets[label] || 0,
  }));
}

function computeUsersHittingLimitTrend(
  usersHittingLimit: UserAnalyticsReportCharts["users_hitting_limit"],
) {
  const dailyData: Record<string, { GUEST: number; GOOGLE: number }> = {};
  usersHittingLimit.forEach((item) => {
    if (!dailyData[item.date]) dailyData[item.date] = { GUEST: 0, GOOGLE: 0 };
    dailyData[item.date][item.auth_type as "GUEST" | "GOOGLE"] += 1;
  });
  return Object.entries(dailyData)
    .map(([date, counts]) => ({
      date,
      GUEST: counts.GUEST,
      GOOGLE: counts.GOOGLE,
    }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

function ReportContent({
  stats,
  charts,
}: {
  stats: UserAnalyticsStatsResponse;
  charts: UserAnalyticsReportCharts | null;
}) {
  const roundsDistributionBySession = useMemo(
    () =>
      charts
        ? computeRoundsDistributionBySession(charts.conversation_rounds)
        : [],
    [charts],
  );
  const roundsDistributionByUser = useMemo(
    () =>
      charts
        ? computeRoundsDistributionByUser(charts.user_rounds_distribution)
        : [],
    [charts],
  );
  const usersHittingLimitTrend = useMemo(
    () =>
      charts ? computeUsersHittingLimitTrend(charts.users_hitting_limit) : [],
    [charts],
  );
  const newUsers = charts?.new_users ?? [];
  const popularAgents = charts?.popular_agents ?? [];

  return (
    <>
      <StatsCards stats={stats} />
      <Row gutter={[16, 16]} style={{ marginTop: "24px" }}>
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
        <Col xs={24} lg={12}>
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
                  },
                  {
                    title: "真实发起聊天人数",
                    dataIndex: "user_count",
                    key: "user_count",
                    width: 150,
                  },
                  {
                    title: "开口率",
                    dataIndex: "open_rate",
                    key: "open_rate",
                    width: 120,
                    render: (v: number) => `${v.toFixed(2)}%`,
                  },
                  {
                    title: "总聊天轮数",
                    dataIndex: "total_rounds",
                    key: "total_rounds",
                    width: 120,
                  },
                  {
                    title: "人均聊天轮数",
                    dataIndex: "avg_rounds_per_user",
                    key: "avg_rounds_per_user",
                    width: 130,
                    render: (v: number) => v.toFixed(2),
                  },
                  {
                    title: ">=5轮会话百分比",
                    dataIndex: "pct_sessions_ge_5",
                    key: "pct_sessions_ge_5",
                    width: 150,
                    render: (v: number) => `${v.toFixed(2)}%`,
                  },
                  {
                    title: ">=10轮会话百分比",
                    dataIndex: "pct_sessions_ge_10",
                    key: "pct_sessions_ge_10",
                    width: 160,
                    render: (v: number) => `${v.toFixed(2)}%`,
                  },
                ]}
                dataSource={popularAgents}
                rowKey="agent_name"
                pagination={false}
                size="small"
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>
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
      </Row>
    </>
  );
}

function StatsCards({ stats }: { stats: UserAnalyticsStatsResponse }) {
  return (
    <>
      <Row gutter={[16, 16]} style={{ marginBottom: "16px" }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="消息数"
              value={stats.total_user_messages}
              prefix={<MessageOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="生图请求数"
              value={stats.total_image_generation_requests}
              prefix={<PictureOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="语音通话次数"
              value={stats.total_live_chat_sessions}
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="语音播报次数"
              value={stats.total_voice_requests}
              prefix={<SoundOutlined />}
            />
          </Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginBottom: "16px" }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="用户数"
              value={stats.total_new_users}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="发起聊天的人数"
              value={stats.total_chat_initiators}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="包含用户消息的会话数"
              value={stats.total_active_sessions}
              prefix={<MessageOutlined />}
            />
          </Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginBottom: "16px" }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="人均消息数"
              value={stats.avg_messages_per_user.toFixed(1)}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="人均会话数"
              value={stats.avg_sessions_per_user.toFixed(1)}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="人均语音请求数"
              value={stats.avg_voice_requests_per_user.toFixed(1)}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="每会话平均轮数"
              value={stats.avg_rounds_per_session.toFixed(1)}
            />
          </Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginBottom: "16px" }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="开口率"
              value={stats.new_user_open_rate.toFixed(2)}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginBottom: "16px" }}>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="生图成功次数"
              value={stats.total_image_generation_success}
              prefix={<PictureOutlined />}
              valueStyle={{ color: "#3f8600" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="生图失败次数"
              value={stats.total_image_generation_failures}
              prefix={<PictureOutlined />}
              valueStyle={{ color: "#cf1322" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="生图成功率"
              value={stats.image_generation_success_rate.toFixed(2)}
              suffix="%"
              prefix={<PictureOutlined />}
              valueStyle={{
                color:
                  stats.image_generation_success_rate >= 80
                    ? "#3f8600"
                    : stats.image_generation_success_rate >= 50
                      ? "#faad14"
                      : "#cf1322",
              }}
            />
          </Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginBottom: "16px" }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="新生成次数"
              value={stats.total_image_new_generation}
              prefix={<PictureOutlined />}
              valueStyle={{ color: "#3f8600" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="兜底图片次数"
              value={stats.total_image_fallback_used}
              prefix={<PictureOutlined />}
              valueStyle={{ color: "#faad14" }}
            />
          </Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginBottom: "16px" }}>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="发起语音通话人数"
              value={stats.total_live_chat_users}
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="总通话时长（秒）"
              value={stats.total_live_chat_duration}
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="人均通话次数"
              value={stats.avg_live_chat_sessions_per_user.toFixed(2)}
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="人均通话时长（秒）"
              value={stats.avg_live_chat_duration_per_user.toFixed(2)}
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="每次平均时长（秒）"
              value={stats.avg_live_chat_duration_per_session.toFixed(2)}
              prefix={<PhoneOutlined />}
            />
          </Card>
        </Col>
      </Row>
    </>
  );
}

export const UserAnalyticsReportsPage: React.FC = () => {
  const [reportType, setReportType] = useState<ReportType>("daily");
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState<UserAnalyticsReportItem[]>([]);

  const loadReports = useCallback(async () => {
    setLoading(true);
    try {
      const data = await userAnalyticsApi.getReports({
        report_type: reportType,
        limit: 30,
      });
      setReports(data.reports);
      message.success("数据加载成功");
    } catch (error) {
      console.error("加载报告失败:", error);
      message.error("加载报告失败");
    } finally {
      setLoading(false);
    }
  }, [reportType]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const items = reports.map((report) => ({
    key: report.id,
    label: `${report.report_date}（${REPORT_TYPE_LABELS[report.report_type]}）`,
    children: <ReportContent stats={report.stats} charts={report.charts} />,
  }));

  return (
    <div style={{ padding: "24px" }}>
      <Card style={{ marginBottom: "24px" }}>
        <Space>
          <span>报告类型：</span>
          <Select
            value={reportType}
            onChange={(v) => setReportType(v)}
            style={{ width: 120 }}
            options={[
              { value: "daily", label: "日报" },
              { value: "weekly", label: "周报" },
            ]}
          />
          <span style={{ color: "#999", fontSize: 12 }}>
            数据由定时任务预计算，每日/每周更新
          </span>
          <ReloadOutlined
            onClick={loadReports}
            style={{ cursor: "pointer", fontSize: 16 }}
            title="刷新"
          />
        </Space>
      </Card>

      <Spin spinning={loading}>
        {reports.length === 0 && !loading ? (
          <Empty description="暂无预计算报告数据" />
        ) : (
          <Collapse items={items} defaultActiveKey={items[0]?.key} />
        )}
      </Spin>
    </div>
  );
};
