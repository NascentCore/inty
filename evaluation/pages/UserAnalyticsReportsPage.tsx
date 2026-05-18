/**
 * 用户数据分析日报周报页面
 * 展示全部用户的预计算聚合统计，数据由定时任务预计算，不包含对话详情
 * CREATED_BY_AGENT
 */

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Button,
  Card,
  Select,
  Space,
  Row,
  Col,
  Avatar,
  Statistic,
  Collapse,
  Table,
  message,
  Spin,
  Empty,
  Image,
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
import type { Data } from "plotly.js";
import { userAnalyticsApi } from "../services/api";
import type {
  DailyVoiceAudiosResponse,
  UserAnalyticsReportItem,
  UserAnalyticsStatsResponse,
  UserAnalyticsReportCharts,
  VoiceAudioGroupByUserAgent,
} from "../types";
import {
  DAILY_USAGE_CHART_METRICS,
  DAILY_IMAGE_USAGE_CHART_METRICS,
  DAILY_USAGE_HAS_SECONDARY_AXIS,
  DAILY_IMAGE_USAGE_HAS_SECONDARY_AXIS,
  DAILY_USAGE_SECONDARY_AXIS_COLOR,
  DAILY_USAGE_SECONDARY_AXIS_TITLE,
  DAILY_USAGE_IMAGE_AI_REPLY_RATIO_COLOR,
  DAILY_USAGE_IMAGE_AI_REPLY_RATIO_LABEL,
  DAILY_USAGE_VOICE_MESSAGE_RATIO_COLOR,
  DAILY_USAGE_VOICE_MESSAGE_RATIO_LABEL,
  DAILY_IMAGE_USAGE_SECONDARY_AXIS_COLOR,
  DAILY_IMAGE_USAGE_SECONDARY_AXIS_TITLE,
  DAILY_TOP_AGENTS_LIMIT,
  buildDailyTopAgentsTrendSeries,
  buildDailyImageUsageSeries,
  buildDailyUsageSeries,
  buildImageRequestsPerAiMessageRatioValues,
  buildVoiceRequestsPerMessageRatioValues,
  buildRollingDailyImageUsageSeries,
  buildRollingDailyUsageSeries,
  buildDailyUsageTickText,
  removeOpeningVoiceMessageAudios,
  sortReportsByDateDesc,
  WEEKLY_USAGE_ROLLING_WINDOW_DAYS,
} from "../utils/userAnalyticsReports";
import { USER_ANALYTICS_GENERATED_IMAGE_PREVIEW_STYLE } from "../utils/userAnalyticsReportImagePreview";
import GeneratedImageDetailModal from "../components/common/GeneratedImageDetailModal";
import { PerformanceAnalyticsSection } from "../components/userAnalytics/PerformanceAnalyticsSection";
import {
  buildGeneratedImageDetailFromDailyReportItem,
  type GeneratedImageDetail,
} from "../utils/generatedImageDetail";
import {
  buildVoiceRecordingPageUrl,
  getEvaluationBaseUrl,
} from "../utils/profileLinks";
import {
  OpsAgentDetailModal,
  OpsUserDetailModal,
} from "../components/common/OpsEntityDetailModals";

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

const USAGE_CHART_HEIGHT = 360;
const USAGE_MARKER_SIZE = 6;
const REPORTS_LIMIT = 30;
const DAILY_LATEST_LIMIT = 1;
const DAILY_GENERATED_IMAGES_PREVIEW_LIMIT = 60;
const DAILY_VOICE_AUDIOS_PREVIEW_LIMIT = 20;
const TOP_AGENTS_TREND_CHART_HEIGHT = 420;
const TOP_AGENT_MARKER_SIZE = 20;
const TOP_AGENT_TREND_COLORS = [
  "#1677ff",
  "#52c41a",
  "#faad14",
  "#eb2f96",
  "#13c2c2",
  "#722ed1",
  "#fa541c",
  "#2f54eb",
  "#a0d911",
  "#f759ab",
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

function getAgentIconLabel(agentName: string): string {
  const normalizedName = agentName.trim();
  if (!normalizedName) {
    return "?";
  }
  return normalizedName.slice(0, 1).toUpperCase();
}

function getAgentTrendColor(agentName: string): string {
  let hash = 0;
  for (let index = 0; index < agentName.length; index += 1) {
    hash = (hash * 31 + agentName.charCodeAt(index)) % 2147483647;
  }
  const colorIndex = Math.abs(hash) % TOP_AGENT_TREND_COLORS.length;
  return TOP_AGENT_TREND_COLORS[colorIndex];
}

export function VoiceAudiosGroupCard({
  title,
  groups,
  previewLimit,
}: {
  title: string;
  groups: VoiceAudioGroupByUserAgent[];
  previewLimit: number;
}) {
  const baseUrl = getEvaluationBaseUrl();
  const [detailUserId, setDetailUserId] = useState<string | null>(null);
  const [detailAgentId, setDetailAgentId] = useState<string | null>(null);

  if (groups.length === 0) {
    return (
      <Card title={title} style={{ marginTop: "24px" }}>
        <Empty description="当天无数据" />
      </Card>
    );
  }
  return (
    <Card
      title={`${title}（${groups.length} 组）`}
      style={{ marginTop: "24px" }}
      styles={{ body: { maxHeight: 420, overflowY: "auto" } }}
    >
      {groups.slice(0, previewLimit).map((group, idx) => (
        <div
          key={`${group.user_id}-${group.agent_id}-${idx}`}
          style={{
            marginBottom: 16,
            padding: 12,
            backgroundColor: "#fafafa",
            borderRadius: 8,
          }}
        >
          <div
            style={{
              fontSize: 12,
              color: "#666",
              marginBottom: 8,
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            <div style={{ wordBreak: "break-all" }}>
              用户ID:{" "}
              <Button
                type="link"
                size="small"
                style={{ padding: 0, height: "auto", fontFamily: "monospace" }}
                onClick={() => setDetailUserId(group.user_id)}
              >
                {group.user_id}
              </Button>
            </div>
            <div style={{ wordBreak: "break-all" }}>
              角色: {group.agent_name || "-"} · Agent ID:{" "}
              <Button
                type="link"
                size="small"
                style={{ padding: 0, height: "auto", fontFamily: "monospace" }}
                onClick={() => setDetailAgentId(group.agent_id)}
              >
                {group.agent_id}
              </Button>
            </div>
          </div>
          {group.audios.map((a, i) => (
            <div key={i} style={{ marginTop: 8 }}>
              <Space size={8} align="center">
                <span style={{ fontSize: 12, color: "#999" }}>Voice</span>
                <a
                  href={a.audio_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontSize: 12 }}
                >
                  Open recording
                </a>
                <a
                  href={buildVoiceRecordingPageUrl(baseUrl, {
                    audioUrl: a.audio_url,
                    userId: group.user_id,
                    agentId: group.agent_id,
                    agentName: group.agent_name,
                    createdAt: a.created_at,
                    durationSeconds: a.duration_seconds,
                    messageId: a.message_id,
                  })}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Permanent link (ops recording page)"
                  style={{ fontSize: 12 }}
                >
                  Permanent link
                </a>
                {a.duration_seconds != null && (
                  <span style={{ fontSize: 12, color: "#999" }}>
                    {a.duration_seconds.toFixed(1)}s
                  </span>
                )}
              </Space>
              <audio
                src={a.audio_url}
                controls
                preload="metadata"
                style={{
                  width: "100%",
                  maxWidth: 320,
                  height: 32,
                  marginTop: 4,
                }}
              />
              <div
                style={{
                  fontSize: 11,
                  fontFamily: "monospace",
                  color: "#999",
                  wordBreak: "break-all",
                  marginTop: 4,
                }}
                title={a.audio_url}
              >
                {a.audio_url}
              </div>
            </div>
          ))}
        </div>
      ))}
      {groups.length > previewLimit && (
        <div style={{ marginTop: 12, color: "#999", fontSize: 12 }}>
          仅展示前 {previewLimit} 组
        </div>
      )}
      <OpsUserDetailModal
        open={detailUserId != null}
        userId={detailUserId ?? ""}
        onClose={() => setDetailUserId(null)}
      />
      <OpsAgentDetailModal
        open={detailAgentId != null}
        agentId={detailAgentId ?? ""}
        onClose={() => setDetailAgentId(null)}
      />
    </Card>
  );
}

function ReportContent({
  stats,
  charts,
  reportType,
  reportDate,
  voiceAudiosCache,
  setVoiceAudiosCache,
}: {
  stats: UserAnalyticsStatsResponse;
  charts: UserAnalyticsReportCharts | null;
  reportType: ReportType;
  reportDate?: string;
  voiceAudiosCache: Record<string, DailyVoiceAudiosResponse | null>;
  setVoiceAudiosCache: React.Dispatch<
    React.SetStateAction<Record<string, DailyVoiceAudiosResponse | null>>
  >;
}) {
  const [previewImageDetail, setPreviewImageDetail] =
    useState<GeneratedImageDetail | null>(null);
  const [voiceAudiosLoading, setVoiceAudiosLoading] = useState(false);
  useEffect(() => {
    if (
      reportType !== "daily" ||
      !reportDate ||
      voiceAudiosCache[reportDate] !== undefined
    ) {
      return;
    }
    setVoiceAudiosLoading(true);
    userAnalyticsApi
      .getDailyVoiceAudios(reportDate)
      .then((data) => {
        const normalizedVoiceAudios = removeOpeningVoiceMessageAudios(data);
        setVoiceAudiosCache((prev) => ({
          ...prev,
          [reportDate!]: normalizedVoiceAudios,
        }));
      })
      .finally(() => setVoiceAudiosLoading(false));
  }, [reportType, reportDate, voiceAudiosCache, setVoiceAudiosCache]);
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
  const generatedImages = charts?.generated_images ?? [];
  const dailyMostDiscussedAgent = charts?.daily_most_discussed_agent ?? null;
  const previewGeneratedImages = generatedImages.slice(
    0,
    DAILY_GENERATED_IMAGES_PREVIEW_LIMIT,
  );

  return (
    <>
      <StatsCards stats={stats} />
      {reportType === "daily" && (
        <Card title="当日聊天轮数最高角色" style={{ marginTop: "24px" }}>
          {dailyMostDiscussedAgent ? (
            <Space size={12} align="center">
              <Avatar
                style={{
                  backgroundColor: getAgentTrendColor(
                    dailyMostDiscussedAgent.agent_name,
                  ),
                }}
              >
                {getAgentIconLabel(dailyMostDiscussedAgent.agent_name)}
              </Avatar>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <div style={{ fontWeight: 600 }}>
                  {dailyMostDiscussedAgent.agent_name}
                </div>
                <div style={{ color: "#999", fontSize: 12 }}>
                  聊天轮数 {dailyMostDiscussedAgent.total_rounds}，发起聊天人数{" "}
                  {dailyMostDiscussedAgent.user_count}
                </div>
              </div>
            </Space>
          ) : (
            <Empty description="当天暂无聊天角色热度数据" />
          )}
        </Card>
      )}
      {reportType === "daily" && (
        <Card
          title={`当天生成图片（${generatedImages.length}）`}
          style={{ marginTop: "24px" }}
          styles={{ body: { maxHeight: 420, overflowY: "auto" } }}
        >
          {generatedImages.length > 0 ? (
            <>
              {generatedImages.length >
                DAILY_GENERATED_IMAGES_PREVIEW_LIMIT && (
                <div style={{ marginBottom: 12, color: "#999", fontSize: 12 }}>
                  仅展示最新 {DAILY_GENERATED_IMAGES_PREVIEW_LIMIT} 张
                </div>
              )}
              <Row gutter={[12, 12]}>
                {previewGeneratedImages.map((item) => {
                  const detail =
                    buildGeneratedImageDetailFromDailyReportItem(item);
                  return (
                    <Col key={item.id} xs={12} sm={8} md={6} lg={4} xl={3}>
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 6,
                        }}
                      >
                        <Image
                          src={item.image_url}
                          alt={`generated-${item.id}`}
                          preview={false}
                          style={{
                            ...USER_ANALYTICS_GENERATED_IMAGE_PREVIEW_STYLE,
                            cursor: "pointer",
                          }}
                          onClick={() => setPreviewImageDetail(detail)}
                        />
                        <div
                          style={{
                            color: "#999",
                            fontSize: 12,
                            lineHeight: 1.2,
                          }}
                        >
                          {item.created_at
                            ? item.created_at.replace("T", " ").slice(0, 19)
                            : "时间未知"}
                        </div>
                        <div
                          style={{
                            color: "#999",
                            fontSize: 12,
                            lineHeight: 1.2,
                          }}
                        >
                          {detail.isMatchedFallback
                            ? "类型: 兜底生图（命中历史图）"
                            : `模型: ${detail.model || "未知模型"}`}
                        </div>
                      </div>
                    </Col>
                  );
                })}
              </Row>
            </>
          ) : (
            <Empty description="当天无生图" />
          )}
        </Card>
      )}
      {reportType === "daily" && reportDate && (
        <>
          {voiceAudiosLoading ? (
            <Card
              title="当天语音播报（按用户-角色）"
              style={{ marginTop: "24px" }}
            >
              <Spin />
            </Card>
          ) : voiceAudiosCache[reportDate] ? (
            <>
              <VoiceAudiosGroupCard
                title="当天语音播报（按用户-角色）"
                groups={voiceAudiosCache[reportDate]!.voice_message_audios}
                previewLimit={DAILY_VOICE_AUDIOS_PREVIEW_LIMIT}
              />
              <VoiceAudiosGroupCard
                title="当天语音通话录音（按用户-角色）"
                groups={voiceAudiosCache[reportDate]!.voice_call_audios}
                previewLimit={DAILY_VOICE_AUDIOS_PREVIEW_LIMIT}
              />
            </>
          ) : null}
        </>
      )}
      <GeneratedImageDetailModal
        open={!!previewImageDetail}
        onClose={() => setPreviewImageDetail(null)}
        detail={previewImageDetail}
        title="图片详情"
      />
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
  const [reports, setReports] = useState<UserAnalyticsReportItem[]>([]);
  const [usageReports, setUsageReports] = useState<UserAnalyticsReportItem[]>(
    [],
  );
  const [loadingReports, setLoadingReports] = useState(false);
  const [loadingUsage, setLoadingUsage] = useState(false);
  const [voiceAudiosCache, setVoiceAudiosCache] = useState<
    Record<string, DailyVoiceAudiosResponse | null>
  >({});
  const requestIdRef = useRef(0);

  const isStaleRequest = useCallback(
    (requestId: number) => requestId !== requestIdRef.current,
    [],
  );

  const loadDailyFullReports = useCallback(
    (requestId: number) => {
      userAnalyticsApi
        .getReports({
          report_type: "daily",
          limit: REPORTS_LIMIT,
        })
        .then((data) => {
          if (isStaleRequest(requestId)) return;
          setReports(data.reports);
        })
        .catch((error) => {
          if (isStaleRequest(requestId)) return;
          console.error("加载更多日报失败:", error);
          message.warning("加载更多日报失败");
        });
    },
    [isStaleRequest],
  );

  const loadDailyLatestReport = useCallback(
    (requestId: number) => {
      userAnalyticsApi
        .getReports({
          report_type: "daily",
          limit: DAILY_LATEST_LIMIT,
        })
        .then((data) => {
          if (isStaleRequest(requestId)) return;
          setReports(data.reports);
          message.success("数据加载成功");
          if (data.reports.length > 0) {
            loadDailyFullReports(requestId);
          }
        })
        .catch((error) => {
          if (isStaleRequest(requestId)) return;
          console.error("加载日报失败:", error);
          message.error("加载日报失败");
        })
        .finally(() => {
          if (isStaleRequest(requestId)) return;
          setLoadingReports(false);
        });
    },
    [isStaleRequest, loadDailyFullReports],
  );

  const loadDailyUsageReports = useCallback(
    (requestId: number) => {
      userAnalyticsApi
        .getReports({
          report_type: "daily",
          limit: REPORTS_LIMIT,
          include_charts: false,
        })
        .then((data) => {
          if (isStaleRequest(requestId)) return;
          setUsageReports(data.reports);
        })
        .catch((error) => {
          if (isStaleRequest(requestId)) return;
          console.error("加载每日用量曲线失败:", error);
          message.warning("每日用量曲线加载失败");
        })
        .finally(() => {
          if (isStaleRequest(requestId)) return;
          setLoadingUsage(false);
        });
    },
    [isStaleRequest],
  );

  const loadDailyReports = useCallback(() => {
    const requestId = ++requestIdRef.current;
    setReports([]);
    setUsageReports([]);
    setLoadingReports(true);
    setLoadingUsage(true);
    loadDailyLatestReport(requestId);
    loadDailyUsageReports(requestId);
  }, [loadDailyLatestReport, loadDailyUsageReports]);

  const loadWeeklyReports = useCallback(() => {
    const requestId = ++requestIdRef.current;

    setReports([]);
    setUsageReports([]);
    setLoadingReports(true);
    setLoadingUsage(true);
    loadDailyUsageReports(requestId);

    userAnalyticsApi
      .getReports({
        report_type: "weekly",
        limit: REPORTS_LIMIT,
      })
      .then((data) => {
        if (isStaleRequest(requestId)) return;
        setReports(data.reports);
        message.success("数据加载成功");
      })
      .catch((error) => {
        if (isStaleRequest(requestId)) return;
        console.error("加载周报失败:", error);
        message.error("加载周报失败");
      })
      .finally(() => {
        if (isStaleRequest(requestId)) return;
        setLoadingReports(false);
      });
  }, [isStaleRequest, loadDailyUsageReports]);

  const loadReports = useCallback(() => {
    if (reportType === "daily") {
      loadDailyReports();
      return;
    }
    loadWeeklyReports();
  }, [reportType, loadDailyReports, loadWeeklyReports]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const sortedReports = useMemo(
    () => sortReportsByDateDesc(reports),
    [reports],
  );
  const usageSeries = useMemo(() => {
    if (reportType === "weekly") {
      return buildRollingDailyUsageSeries(
        usageReports,
        WEEKLY_USAGE_ROLLING_WINDOW_DAYS,
      );
    }
    return buildDailyUsageSeries(usageReports);
  }, [reportType, usageReports]);
  const voiceRequestsPerMessageRatioValues = useMemo(
    () => buildVoiceRequestsPerMessageRatioValues(usageSeries),
    [usageSeries],
  );
  const hasVoiceRequestsPerMessageRatio =
    voiceRequestsPerMessageRatioValues.length > 0;
  const imageRequestsPerAiMessageRatioValues = useMemo(
    () => buildImageRequestsPerAiMessageRatioValues(usageSeries),
    [usageSeries],
  );
  const hasImageRequestsPerAiMessageRatio =
    imageRequestsPerAiMessageRatioValues.length > 0;
  const imageUsageSeries = useMemo(() => {
    if (reportType === "weekly") {
      return buildRollingDailyImageUsageSeries(
        usageReports,
        WEEKLY_USAGE_ROLLING_WINDOW_DAYS,
      );
    }
    return buildDailyImageUsageSeries(usageReports);
  }, [reportType, usageReports]);
  const usageChartTitle =
    reportType === "weekly" ? "每周用量曲线" : "每日用量曲线";
  const imageUsageChartTitle =
    reportType === "weekly" ? "每周生图用量" : "每日生图用量";
  const usageEmptyDescription =
    reportType === "weekly"
      ? "暂无日报数据，无法计算近7天用量"
      : "暂无日报数据";

  const dailyUsagePlotData = useMemo(() => {
    if (!usageSeries) {
      return [];
    }
    const traces: Data[] = DAILY_USAGE_CHART_METRICS.map((metric) => ({
      x: usageSeries.dates,
      y: usageSeries.valuesByMetric[metric.key],
      name: metric.label,
      type: "scatter",
      mode: "lines+markers",
      marker: { size: USAGE_MARKER_SIZE, color: metric.color },
      line: { color: metric.color },
      ...(metric.axis === "y2" ? { yaxis: "y2" } : {}),
    }));
    traces.push({
      x: usageSeries.dates,
      y: voiceRequestsPerMessageRatioValues,
      name: DAILY_USAGE_VOICE_MESSAGE_RATIO_LABEL,
      type: "scatter",
      mode: "lines+markers",
      marker: {
        size: USAGE_MARKER_SIZE,
        color: DAILY_USAGE_VOICE_MESSAGE_RATIO_COLOR,
      },
      line: { color: DAILY_USAGE_VOICE_MESSAGE_RATIO_COLOR },
      yaxis: "y3",
      hovertemplate:
        "日期: %{x}<br>语音播报次数 / 消息数: %{y:.2%}<extra></extra>",
    });
    traces.push({
      x: usageSeries.dates,
      y: imageRequestsPerAiMessageRatioValues,
      name: DAILY_USAGE_IMAGE_AI_REPLY_RATIO_LABEL,
      type: "scatter",
      mode: "lines+markers",
      marker: {
        size: USAGE_MARKER_SIZE,
        color: DAILY_USAGE_IMAGE_AI_REPLY_RATIO_COLOR,
      },
      line: { color: DAILY_USAGE_IMAGE_AI_REPLY_RATIO_COLOR },
      yaxis: "y4",
      hovertemplate:
        "日期: %{x}<br>生图请求数 / AI回复消息数: %{y:.2%}<extra></extra>",
    });
    return traces;
  }, [
    usageSeries,
    voiceRequestsPerMessageRatioValues,
    imageRequestsPerAiMessageRatioValues,
  ]);
  const dailyUsageXAxisTickText = useMemo(() => {
    if (!usageSeries) {
      return [];
    }
    return buildDailyUsageTickText(usageSeries.dates);
  }, [usageSeries]);
  const dailyImageUsagePlotData = useMemo(() => {
    if (!imageUsageSeries) {
      return [];
    }
    return DAILY_IMAGE_USAGE_CHART_METRICS.map((metric) => ({
      x: imageUsageSeries.dates,
      y: imageUsageSeries.valuesByMetric[metric.key],
      name: metric.label,
      type: "scatter",
      mode: "lines+markers",
      marker: { size: USAGE_MARKER_SIZE, color: metric.color },
      line: { color: metric.color },
      ...(metric.axis === "y2" ? { yaxis: "y2" } : {}),
    }));
  }, [imageUsageSeries]);
  const dailyImageUsageXAxisTickText = useMemo(() => {
    if (!imageUsageSeries) {
      return [];
    }
    return buildDailyUsageTickText(imageUsageSeries.dates);
  }, [imageUsageSeries]);
  const dailyTopAgentsTrendSeries = useMemo(
    () => buildDailyTopAgentsTrendSeries(usageReports, DAILY_TOP_AGENTS_LIMIT),
    [usageReports],
  );
  const dailyTopAgentsPlotData = useMemo(() => {
    if (!dailyTopAgentsTrendSeries) {
      return [];
    }
    return dailyTopAgentsTrendSeries.lines.map((line) => {
      const traceColor = getAgentTrendColor(line.agent_name);
      return {
        x: line.points.map((point) => point.date),
        y: line.points.map((point) => point.rank),
        customdata: line.points.map((point) => [
          point.total_rounds,
          point.user_count,
        ]),
        name: line.agent_name,
        type: "scatter",
        mode: "lines+markers+text",
        text: line.points.map(() => getAgentIconLabel(line.agent_name)),
        textposition: "middle center",
        textfont: {
          color: "#ffffff",
          size: 10,
        },
        marker: {
          size: TOP_AGENT_MARKER_SIZE,
          color: traceColor,
          line: { color: "#ffffff", width: 1 },
        },
        line: { color: traceColor, width: 2 },
        hovertemplate:
          "角色: %{fullData.name}<br>" +
          "日期: %{x}<br>" +
          "当日排名: #%{y}<br>" +
          "聊天轮数: %{customdata[0]}<br>" +
          "发起聊天人数: %{customdata[1]}<extra></extra>",
      };
    });
  }, [dailyTopAgentsTrendSeries]);
  const dailyTopAgentsXAxisTickText = useMemo(() => {
    if (!dailyTopAgentsTrendSeries) {
      return [];
    }
    return buildDailyUsageTickText(dailyTopAgentsTrendSeries.dates);
  }, [dailyTopAgentsTrendSeries]);

  const items = useMemo(
    () =>
      sortedReports.map((report) => ({
        key: report.id,
        label: `${report.report_date}（${REPORT_TYPE_LABELS[report.report_type]}）`,
        children: (
          <ReportContent
            stats={report.stats}
            charts={report.charts}
            reportType={report.report_type}
            reportDate={report.report_date}
            voiceAudiosCache={voiceAudiosCache}
            setVoiceAudiosCache={setVoiceAudiosCache}
          />
        ),
      })),
    [sortedReports, voiceAudiosCache],
  );

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

      <Card title={usageChartTitle} style={{ marginBottom: "24px" }}>
        <Spin spinning={loadingUsage}>
          {usageSeries ? (
            <Plot
              data={dailyUsagePlotData}
              layout={{
                height: USAGE_CHART_HEIGHT,
                hovermode: "x unified",
                xaxis: {
                  title: "日期",
                  tickmode: "array",
                  tickvals: usageSeries.dates,
                  ticktext: dailyUsageXAxisTickText,
                },
                yaxis: { title: "用量" },
                ...(DAILY_USAGE_HAS_SECONDARY_AXIS
                  ? {
                      yaxis2: {
                        title: {
                          text: DAILY_USAGE_SECONDARY_AXIS_TITLE,
                          font: { color: DAILY_USAGE_SECONDARY_AXIS_COLOR },
                        },
                        tickfont: { color: DAILY_USAGE_SECONDARY_AXIS_COLOR },
                        side: "right",
                        overlaying: "y",
                        rangemode: "tozero",
                        showgrid: false,
                        zeroline: false,
                        ...(hasVoiceRequestsPerMessageRatio ||
                        hasImageRequestsPerAiMessageRatio
                          ? { anchor: "free", position: 0.93 }
                          : {}),
                      },
                      margin: {
                        r:
                          hasVoiceRequestsPerMessageRatio ||
                          hasImageRequestsPerAiMessageRatio
                            ? 180
                            : 80,
                      },
                    }
                  : {}),
                ...(hasVoiceRequestsPerMessageRatio
                  ? {
                      yaxis3: {
                        title: {
                          text: DAILY_USAGE_VOICE_MESSAGE_RATIO_LABEL,
                          font: {
                            color: DAILY_USAGE_VOICE_MESSAGE_RATIO_COLOR,
                          },
                        },
                        tickfont: {
                          color: DAILY_USAGE_VOICE_MESSAGE_RATIO_COLOR,
                        },
                        tickformat: ".0%",
                        side: "right",
                        overlaying: "y",
                        anchor: "free",
                        position: 1,
                        rangemode: "tozero",
                        showgrid: false,
                        zeroline: false,
                      },
                    }
                  : {}),
                ...(hasImageRequestsPerAiMessageRatio
                  ? {
                      yaxis4: {
                        title: {
                          text: DAILY_USAGE_IMAGE_AI_REPLY_RATIO_LABEL,
                          font: {
                            color: DAILY_USAGE_IMAGE_AI_REPLY_RATIO_COLOR,
                          },
                        },
                        tickfont: {
                          color: DAILY_USAGE_IMAGE_AI_REPLY_RATIO_COLOR,
                        },
                        tickformat: ".0%",
                        side: "right",
                        overlaying: "y",
                        anchor: "free",
                        position: 0.97,
                        rangemode: "tozero",
                        showgrid: false,
                        zeroline: false,
                      },
                    }
                  : {}),
                legend: { orientation: "h" },
              }}
              style={{ width: "100%", height: "100%" }}
            />
          ) : loadingUsage ? (
            <div style={{ height: USAGE_CHART_HEIGHT }} />
          ) : (
            <Empty description={usageEmptyDescription} />
          )}
        </Spin>
      </Card>
      <Card title={imageUsageChartTitle} style={{ marginBottom: "24px" }}>
        <Spin spinning={loadingUsage}>
          {imageUsageSeries ? (
            <Plot
              data={dailyImageUsagePlotData}
              layout={{
                height: USAGE_CHART_HEIGHT,
                hovermode: "x unified",
                xaxis: {
                  title: "日期",
                  tickmode: "array",
                  tickvals: imageUsageSeries.dates,
                  ticktext: dailyImageUsageXAxisTickText,
                },
                yaxis: { title: "生图次数" },
                ...(DAILY_IMAGE_USAGE_HAS_SECONDARY_AXIS
                  ? {
                      yaxis2: {
                        title: {
                          text: DAILY_IMAGE_USAGE_SECONDARY_AXIS_TITLE,
                          font: {
                            color: DAILY_IMAGE_USAGE_SECONDARY_AXIS_COLOR,
                          },
                        },
                        tickfont: {
                          color: DAILY_IMAGE_USAGE_SECONDARY_AXIS_COLOR,
                        },
                        ticksuffix: "%",
                        side: "right",
                        overlaying: "y",
                        rangemode: "tozero",
                        showgrid: false,
                        zeroline: false,
                      },
                      margin: { r: 80 },
                    }
                  : {}),
                legend: { orientation: "h" },
              }}
              style={{ width: "100%", height: "100%" }}
            />
          ) : loadingUsage ? (
            <div style={{ height: USAGE_CHART_HEIGHT }} />
          ) : (
            <Empty description={usageEmptyDescription} />
          )}
        </Spin>
      </Card>
      <Card
        title="每日最受欢迎角色（Top 10，按聊天轮数）"
        style={{ marginBottom: "24px" }}
      >
        <Spin spinning={loadingUsage}>
          {dailyTopAgentsTrendSeries ? (
            <>
              <div style={{ color: "#999", fontSize: 12, marginBottom: 8 }}>
                折线连接同一角色在不同日期的排名变化；图标取角色名称首字母。
              </div>
              <Plot
                data={dailyTopAgentsPlotData}
                layout={{
                  height: TOP_AGENTS_TREND_CHART_HEIGHT,
                  hovermode: "closest",
                  xaxis: {
                    title: "日期",
                    tickmode: "array",
                    tickvals: dailyTopAgentsTrendSeries.dates,
                    ticktext: dailyTopAgentsXAxisTickText,
                  },
                  yaxis: {
                    title: "排名（1最高）",
                    autorange: "reversed",
                    dtick: 1,
                    tick0: 1,
                    range: [DAILY_TOP_AGENTS_LIMIT + 0.5, 0.5],
                  },
                  showlegend: false,
                  margin: { t: 20 },
                }}
                style={{ width: "100%", height: "100%" }}
              />
              <div style={{ color: "#999", fontSize: 12, margin: "8px 0" }}>
                每日 Top 10 列表（右侧数字为聊天轮数）
              </div>
              <div
                style={{
                  display: "grid",
                  gridAutoFlow: "column",
                  gridAutoColumns: "minmax(180px, 1fr)",
                  gap: 12,
                  overflowX: "auto",
                  paddingBottom: 6,
                }}
              >
                {dailyTopAgentsTrendSeries.dates.map((date) => {
                  const dailyTopAgents =
                    dailyTopAgentsTrendSeries.dailyTopAgentsByDate[date] ?? [];
                  return (
                    <div
                      key={date}
                      style={{
                        border: "1px solid #f0f0f0",
                        borderRadius: 8,
                        padding: 8,
                      }}
                    >
                      <div
                        style={{
                          fontWeight: 600,
                          marginBottom: 8,
                          fontSize: 12,
                        }}
                      >
                        {date}
                      </div>
                      {dailyTopAgents.length > 0 ? (
                        <div
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: 6,
                          }}
                        >
                          {dailyTopAgents.map((agent) => (
                            <div
                              key={`${date}-${agent.agent_name}`}
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 6,
                              }}
                            >
                              <span
                                style={{
                                  color: "#999",
                                  fontSize: 12,
                                  width: 24,
                                }}
                              >
                                #{agent.rank}
                              </span>
                              <Avatar
                                size={20}
                                style={{
                                  backgroundColor: getAgentTrendColor(
                                    agent.agent_name,
                                  ),
                                  fontSize: 10,
                                }}
                              >
                                {getAgentIconLabel(agent.agent_name)}
                              </Avatar>
                              <span
                                title={agent.agent_name}
                                style={{
                                  fontSize: 12,
                                  flex: 1,
                                  minWidth: 0,
                                  whiteSpace: "nowrap",
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                }}
                              >
                                {agent.agent_name}
                              </span>
                              <span style={{ color: "#999", fontSize: 12 }}>
                                {agent.total_rounds}
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <Empty
                          image={Empty.PRESENTED_IMAGE_SIMPLE}
                          description="暂无数据"
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          ) : loadingUsage ? (
            <div style={{ height: TOP_AGENTS_TREND_CHART_HEIGHT }} />
          ) : (
            <Empty description="暂无日报角色热度数据" />
          )}
        </Spin>
      </Card>
      <PerformanceAnalyticsSection />
      <Spin spinning={loadingReports}>
        {sortedReports.length === 0 ? (
          loadingReports ? null : (
            <Empty description="暂无预计算报告数据" />
          )
        ) : (
          <Collapse items={items} defaultActiveKey={sortedReports[0]?.id} />
        )}
      </Spin>
    </div>
  );
};
