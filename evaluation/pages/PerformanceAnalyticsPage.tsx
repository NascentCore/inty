/**
 * 性能监控页面
 * 展示 LLM 延迟、生图延迟和 Live Chat 延迟趋势
 * CREATED_BY_AGENT
 */

import React, { useState, useEffect, useCallback } from "react";
import {
  Card,
  Select,
  Button,
  Space,
  Row,
  Col,
  Statistic,
  message,
  Spin,
  Empty,
} from "antd";
import { ReloadOutlined, UserOutlined, PhoneOutlined } from "@ant-design/icons";
import Plot from "react-plotly.js";
import { userAnalyticsApi } from "../services/api";
import type {
  LLMLatencyItem,
  ImageGenerationLatencyItem,
  LiveChatLatencyItem,
  LiveChatBasicStatsResponse,
} from "../types";

const { Option } = Select;

export const PerformanceAnalyticsPage: React.FC = () => {
  // 时间范围选择状态
  const [dateRangeType, setDateRangeType] = useState<string>("7");

  // 数据加载状态
  const [loading, setLoading] = useState(false);

  // 数据状态
  const [llmLatency, setLlmLatency] = useState<LLMLatencyItem[]>([]);
  const [imageGenLatency, setImageGenLatency] = useState<
    ImageGenerationLatencyItem[]
  >([]);
  const [liveChatLatency, setLiveChatLatency] = useState<
    LiveChatLatencyItem[]
  >([]);
  const [liveChatStats, setLiveChatStats] =
    useState<LiveChatBasicStatsResponse | null>(null);

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params =
        dateRangeType === "all"
          ? {}
          : { activity_last_days: parseInt(dateRangeType) };

      // 并行加载所有数据
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

      message.success("数据加载成功");
    } catch (error) {
      console.error("加载数据失败:", error);
      message.error("加载数据失败，请重试");
    } finally {
      setLoading(false);
    }
  }, [dateRangeType]);

  // 初始加载
  useEffect(() => {
    loadData();
  }, [loadData]);

  // 格式化时长（秒 -> 分钟）
  const formatDuration = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds.toFixed(0)}秒`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}分${remainingSeconds.toFixed(0)}秒`;
  };

  return (
    <div style={{ padding: "24px" }}>
      <Spin spinning={loading}>
        {/* 筛选器区域 */}
        <Card style={{ marginBottom: "16px" }}>
          <Space size="middle" wrap>
            <Space>
              <span>时间范围：</span>
              <Select
                value={dateRangeType}
                onChange={setDateRangeType}
                style={{ width: 150 }}
              >
                <Option value="7">最近 7 天</Option>
                <Option value="30">最近 30 天</Option>
                <Option value="90">最近 90 天</Option>
                <Option value="all">全部</Option>
              </Select>
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

        {/* Live Chat 统计卡片 */}
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
                  value={formatDuration(liveChatStats.total_duration)}
                  valueStyle={{ color: "#faad14" }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="平均会话时长"
                  value={formatDuration(liveChatStats.avg_duration_per_session)}
                  valueStyle={{ color: "#722ed1" }}
                />
              </Card>
            </Col>
          </Row>
        )}

        {/* 图表区域 */}
        <Row gutter={[16, 16]}>
          {/* LLM 延迟趋势图表 */}
          <Col xs={24} lg={12}>
            <Card title="LLM 延迟趋势（按小时）" style={{ height: "400px" }}>
              {llmLatency.length > 0 ? (
                <Plot
                  data={[
                    {
                      x: llmLatency.map((d) => d.hour),
                      y: llmLatency.map((d) => d.avg_latency),
                      name: "平均延迟",
                      type: "scatter",
                      mode: "lines+markers",
                      line: { color: "#1890ff" },
                      hovertemplate:
                        "时间: %{x}<br>平均延迟: %{y:.3f}s<br>请求数: %{customdata}<extra></extra>",
                      customdata: llmLatency.map((d) => d.count),
                    },
                  ]}
                  layout={{
                    title: "LLM 延迟趋势",
                    height: 300,
                    xaxis: { title: "时间", tickangle: -45 },
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

          {/* 生图延迟趋势图表 */}
          <Col xs={24} lg={12}>
            <Card title="生图耗时趋势（按模型）" style={{ height: "400px" }}>
              {imageGenLatency.length > 0 ? (
                <Plot
                  data={(() => {
                    // 按模型分组数据
                    const modelGroups = imageGenLatency.reduce(
                      (acc, item) => {
                        if (!acc[item.model]) {
                          acc[item.model] = [];
                        }
                        acc[item.model].push(item);
                        return acc;
                      },
                      {} as Record<string, ImageGenerationLatencyItem[]>,
                    );

                    // 为每个模型创建一条线
                    const colors = [
                      "#1890ff",
                      "#52c41a",
                      "#faad14",
                      "#f5222d",
                      "#722ed1",
                      "#13c2c2",
                    ];
                    return Object.entries(modelGroups).map(
                      ([model, data], index) => ({
                        x: data.map((d) => d.hour),
                        y: data.map((d) => d.avg_latency_ms / 1000), // 转换为秒
                        name: model,
                        type: "scatter" as const,
                        mode: "lines+markers" as const,
                        line: { color: colors[index % colors.length] },
                        hovertemplate: `时间: %{x}<br>平均耗时: %{y:.2f}s<br>请求数: %{customdata}<extra>${model}</extra>`,
                        customdata: data.map((d) => d.count),
                      }),
                    );
                  })()}
                  layout={{
                    title: "生图耗时趋势（按模型）",
                    height: 300,
                    xaxis: { title: "时间", tickangle: -45 },
                    yaxis: { title: "平均耗时 (秒)" },
                    hovermode: "closest",
                    legend: { orientation: "h", y: -0.3 },
                  }}
                  style={{ width: "100%", height: "100%" }}
                />
              ) : (
                <Empty description="暂无数据" />
              )}
            </Card>
          </Col>

          {/* Live Chat 延迟趋势图表 */}
          <Col xs={24} lg={24}>
            <Card title="Live Chat 延迟趋势（按小时）" style={{ height: "400px" }}>
              {liveChatLatency.length > 0 ? (
                <Plot
                  data={[
                    {
                      x: liveChatLatency.map((d) => d.hour),
                      y: liveChatLatency.map(
                        (d) => d.avg_connect_latency || null,
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
                      x: liveChatLatency.map((d) => d.hour),
                      y: liveChatLatency.map(
                        (d) => d.avg_first_byte_latency || null,
                      ),
                      name: "首字节延迟",
                      type: "scatter",
                      mode: "lines+markers",
                      line: { color: "#52c41a" },
                      connectgaps: false,
                      hovertemplate:
                        "时间: %{x}<br>首字节延迟: %{y:.1f}ms<extra></extra>",
                    },
                    {
                      x: liveChatLatency.map((d) => d.hour),
                      y: liveChatLatency.map(
                        (d) => d.avg_turn_latency || null,
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
                    xaxis: { title: "时间", tickangle: -45 },
                    yaxis: { title: "延迟 (毫秒)" },
                    hovermode: "closest",
                    legend: { orientation: "h", y: -0.2 },
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
    </div>
  );
};
