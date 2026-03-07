import React, { useCallback, useEffect, useState } from "react";
import {
  Card,
  Select,
  Button,
  Space,
  Row,
  Col,
  Statistic,
  Spin,
  Empty,
} from "antd";
import { ReloadOutlined, UserOutlined, PhoneOutlined } from "@ant-design/icons";
import Plot from "react-plotly.js";
import { userAnalyticsApi } from "../../services/api";
import type {
  LLMLatencyItem,
  ImageGenerationLatencyItem,
  LiveChatLatencyItem,
  LiveChatBasicStatsResponse,
} from "../../types";
import {
  buildPerformanceAnalyticsParams,
  formatDurationFromSeconds,
  groupImageGenerationLatencyByModel,
  PERFORMANCE_DATE_RANGE_OPTIONS,
  type PerformanceDateRangeType,
} from "../../utils/performanceAnalytics";

export function PerformanceAnalyticsSection() {
  const [dateRangeType, setDateRangeType] =
    useState<PerformanceDateRangeType>("7");
  const [loading, setLoading] = useState(false);
  const [llmLatency, setLlmLatency] = useState<LLMLatencyItem[]>([]);
  const [imageGenLatency, setImageGenLatency] = useState<
    ImageGenerationLatencyItem[]
  >([]);
  const [liveChatLatency, setLiveChatLatency] = useState<LiveChatLatencyItem[]>(
    [],
  );
  const [liveChatStats, setLiveChatStats] =
    useState<LiveChatBasicStatsResponse | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);

    const params = buildPerformanceAnalyticsParams(dateRangeType);
    try {
      const [llmRes, imageRes, liveChatLatRes, liveChatStatsRes] =
        await Promise.all([
          userAnalyticsApi.getLLMLatency(params),
          userAnalyticsApi.getImageGenerationLatency(params),
          userAnalyticsApi.getLiveChatLatency(params),
          userAnalyticsApi.getLiveChatStats(params),
        ]);

      setLlmLatency(llmRes.data || []);
      setImageGenLatency(imageRes.data || []);
      setLiveChatLatency(liveChatLatRes.data || []);
      setLiveChatStats(liveChatStatsRes);
    } finally {
      setLoading(false);
    }
  }, [dateRangeType]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const imageGenLatencyByModel =
    groupImageGenerationLatencyByModel(imageGenLatency);

  return (
    <Card
      title="性能监控（LLM / 生图 / Live Chat）"
      style={{ marginBottom: "24px" }}
    >
      <Spin spinning={loading}>
        <Card size="small" style={{ marginBottom: "16px" }}>
          <Space size="middle" wrap>
            <Space>
              <span>时间范围：</span>
              <Select
                value={dateRangeType}
                onChange={setDateRangeType}
                style={{ width: 150 }}
                options={PERFORMANCE_DATE_RANGE_OPTIONS}
              />
            </Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadData}
              loading={loading}
            >
              刷新数据
            </Button>
          </Space>
        </Card>

        {liveChatStats && (
          <Row gutter={[16, 16]} style={{ marginBottom: "16px" }}>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="语音通话用户数"
                  value={liveChatStats.total_users}
                  prefix={<UserOutlined />}
                  valueStyle={{ color: "#1890ff" }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="总会话数"
                  value={liveChatStats.total_sessions}
                  prefix={<PhoneOutlined />}
                  valueStyle={{ color: "#52c41a" }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="总通话时长"
                  value={formatDurationFromSeconds(
                    liveChatStats.total_duration,
                  )}
                  valueStyle={{ color: "#faad14" }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="平均会话时长"
                  value={formatDurationFromSeconds(
                    liveChatStats.avg_duration_per_session,
                  )}
                  valueStyle={{ color: "#722ed1" }}
                />
              </Card>
            </Col>
          </Row>
        )}

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card title="LLM 延迟趋势（按小时）" style={{ height: "450px" }}>
              {llmLatency.length > 0 ? (
                <Plot
                  data={[
                    {
                      x: llmLatency.map((item) => item.hour),
                      y: llmLatency.map((item) => item.avg_latency),
                      name: "平均延迟",
                      type: "scatter",
                      mode: "lines+markers",
                      line: { color: "#1890ff" },
                      customdata: llmLatency.map((item) => item.count),
                      hovertemplate:
                        "时间: %{x}<br>平均延迟: %{y:.3f}s<br>请求数: %{customdata}<extra></extra>",
                    },
                  ]}
                  layout={{
                    title: "LLM 延迟趋势",
                    height: 300,
                    margin: { t: 60, b: 80, l: 50, r: 20 },
                    xaxis: {
                      title: "时间",
                      tickangle: -45,
                      nticks: 10,
                      tickformat: "%m-%d %H:%M",
                    },
                    yaxis: { title: "平均延迟 (秒)" },
                    hovermode: "closest",
                  }}
                  style={{ width: "100%", height: "100%" }}
                />
              ) : (
                <Empty description="暂无数据" />
              )}
            </Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card title="生图耗时趋势（按模型）" style={{ height: "480px" }}>
              {imageGenLatencyByModel.length > 0 ? (
                <Plot
                  data={imageGenLatencyByModel.map((series) => ({
                    x: series.items.map((item) => item.hour),
                    y: series.items.map((item) => item.avg_latency_ms / 1000),
                    name: series.model,
                    type: "scatter" as const,
                    mode: "lines+markers" as const,
                    line: { color: series.color },
                    customdata: series.items.map((item) => item.count),
                    hovertemplate:
                      "时间: %{x}<br>平均耗时: %{y:.2f}s<br>请求数: %{customdata}<extra>" +
                      `${series.model}</extra>`,
                  }))}
                  layout={{
                    title: "生图耗时趋势（按模型）",
                    height: 300,
                    margin: { t: 80, b: 80, l: 50, r: 20 },
                    xaxis: {
                      title: "时间",
                      tickangle: -45,
                      nticks: 10,
                      tickformat: "%m-%d %H:%M",
                    },
                    yaxis: { title: "平均耗时 (秒)" },
                    hovermode: "closest",
                    legend: {
                      orientation: "h",
                      y: 1.15,
                      xanchor: "center",
                      x: 0.5,
                    },
                  }}
                  style={{ width: "100%", height: "100%" }}
                />
              ) : (
                <Empty description="暂无数据" />
              )}
            </Card>
          </Col>

          <Col xs={24} lg={24}>
            <Card
              title="Live Chat 延迟趋势（按小时）"
              style={{ height: "480px" }}
            >
              {liveChatLatency.length > 0 ? (
                <Plot
                  data={[
                    {
                      x: liveChatLatency.map((item) => item.hour),
                      y: liveChatLatency.map(
                        (item) => item.avg_connect_latency || null,
                      ),
                      name: "连接延迟",
                      type: "scatter",
                      mode: "lines+markers",
                      line: { color: "#1890ff" },
                      connectgaps: false,
                      hovertemplate:
                        "时间: %{x}<br>连接延迟: %{y:.1f}ms<extra></extra>",
                    },
                    {
                      x: liveChatLatency.map((item) => item.hour),
                      y: liveChatLatency.map(
                        (item) => item.avg_first_response_after_silence || null,
                      ),
                      name: "静默后首响应",
                      type: "scatter",
                      mode: "lines+markers",
                      line: { color: "#52c41a" },
                      connectgaps: false,
                      hovertemplate:
                        "时间: %{x}<br>静默后首响应: %{y:.1f}ms<extra></extra>",
                    },
                    {
                      x: liveChatLatency.map((item) => item.hour),
                      y: liveChatLatency.map(
                        (item) => item.avg_turn_latency || null,
                      ),
                      name: "平均轮次延迟",
                      type: "scatter",
                      mode: "lines+markers",
                      line: { color: "#faad14" },
                      connectgaps: false,
                      hovertemplate:
                        "时间: %{x}<br>轮次延迟: %{y:.1f}ms<extra></extra>",
                    },
                  ]}
                  layout={{
                    title: "Live Chat 延迟趋势",
                    height: 300,
                    margin: { t: 80, b: 80, l: 50, r: 20 },
                    xaxis: {
                      title: "时间",
                      tickangle: -45,
                      nticks: 10,
                      tickformat: "%m-%d %H:%M",
                    },
                    yaxis: { title: "延迟 (毫秒)" },
                    hovermode: "closest",
                    legend: {
                      orientation: "h",
                      y: 1.15,
                      xanchor: "center",
                      x: 0.5,
                    },
                  }}
                  style={{ width: "100%", height: "100%" }}
                />
              ) : (
                <Empty description="暂无数据" />
              )}
            </Card>
          </Col>
        </Row>
      </Spin>
    </Card>
  );
}
