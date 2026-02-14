/**
 * 评测监控组件
 * 负责实时监控评测进度、显示结果、管理评测状态
 */

import React, { useState, useEffect, useMemo } from "react";
import {
  Card,
  Progress,
  Button,
  Tag,
  Space,
  Alert,
  Row,
  Col,
  Statistic,
  Descriptions,
  Modal,
  message,
  Badge,
  Empty,
} from "antd";
import {
  PlayCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  FireOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import { useEvaluationSession } from "../../hooks/useEvaluationSession";
import { useJsonDisplay } from "../../hooks/useJsonDisplay";
import { MultiAgentChatDisplay } from "./MultiAgentChatDisplay";
import { JsonDisplayModal } from "../common/JsonDisplayModal";
import api from "../../services/api";
import type { EvaluationSession, EvaluationResult } from "../../types";
import { formatUtcTimeRaw } from "../../utils/dateUtils";

type EvaluationStatus = EvaluationSession["status"];

interface EvaluationMonitorProps {
  session: EvaluationSession | null;
  onSessionChange?: (session: EvaluationSession | null) => void;
  showControls?: boolean;
  autoRefresh?: boolean;
}

export const EvaluationMonitor: React.FC<EvaluationMonitorProps> = ({
  session: propSession,
  onSessionChange,
  showControls = true,
  autoRefresh = true,
}) => {
  // 状态管理
  const [results, setResults] = useState<EvaluationResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { jsonModalVisible, jsonData, showJson, hideJson } = useJsonDisplay();

  // 如果没有传入session，则使用hook管理
  const {
    session: hookSession,
    results: hookResults,
    loading: hookLoading,
    error: hookError,
    startSession,
    cancelSession,
    refreshSession,
    refreshResults,
    connectWebSocket,
    disconnectWebSocket,
    isWebSocketConnected,
  } = useEvaluationSession({
    autoRefresh: !propSession && autoRefresh, // 只有没有传入session时才使用hook的autoRefresh
    refreshInterval: 5000,
  });

  // 使用传入的session或hook的session
  const session = propSession || hookSession;

  // 当有传入session时，管理自己的结果数据和刷新逻辑
  useEffect(() => {
    if (propSession?.id) {
      // 使用传入的session时，加载结果
      const loadResults = async () => {
        setLoading(true);
        setError(null);
        try {
          const sessionResults = await api.sessions.getResults(propSession.id);
          setResults(sessionResults);
        } catch (err: unknown) {
          const errMessage =
            err instanceof Error ? err.message : "加载结果失败";
          setError(errMessage);
        } finally {
          setLoading(false);
        }
      };

      loadResults();
    } else if (!propSession) {
      // 没有传入session时，使用hook的数据
      setResults(hookResults);
      setLoading(hookLoading);
      setError(hookError);
    }
  }, [propSession, hookResults, hookLoading, hookError]);

  // 自动刷新逻辑 - 当传入session且需要自动刷新时
  useEffect(() => {
    if (
      propSession &&
      autoRefresh &&
      ["pending", "running"].includes(propSession.status)
    ) {
      const interval = propSession.status === "running" ? 3000 : 10000;

      const timer = setInterval(async () => {
        try {
          console.log(
            `自动刷新评测结果: ${propSession.id}, 状态: ${propSession.status}`,
          );
          const sessionResults = await api.sessions.getResults(propSession.id);
          setResults(sessionResults);

          // 通知父组件刷新session状态
          if (onSessionChange) {
            const updatedSession = await api.sessions.get(propSession.id);
            onSessionChange(updatedSession);
          }
        } catch (err) {
          console.error("自动刷新失败:", err);
        }
      }, interval);

      return () => clearInterval(timer);
    }
  }, [propSession, autoRefresh, onSessionChange]);

  // 状态变化通知
  useEffect(() => {
    if (onSessionChange && session !== propSession && !propSession) {
      onSessionChange(session);
    }
  }, [session, propSession, onSessionChange]);

  // WebSocket连接管理
  useEffect(() => {
    if (
      session &&
      (session.status === "running" || session.status === "pending")
    ) {
      connectWebSocket(session.id);
    } else {
      disconnectWebSocket();
    }

    return () => {
      disconnectWebSocket();
    };
  }, [session, connectWebSocket, disconnectWebSocket]);

  // 计算统计数据
  const statistics = useMemo(() => {
    if (!session || !results) {
      return {
        totalTests: 0,
        completedTests: 0,
        totalAgents: 0,
        averageScore: 0,
        completionRate: 0,
      };
    }

    const totalAgents = session.selected_agents?.length || 0;
    const totalQuestions = session.questions?.length || 0;
    const totalTests = totalAgents * totalQuestions;
    const completedTests = results.length;
    const averageScore =
      results.length > 0
        ? results.reduce(
            (sum, result) => sum + (result.overall_score || 0),
            0,
          ) / results.length
        : 0;
    const completionRate = totalTests > 0 ? completedTests / totalTests : 0;

    return {
      totalTests,
      completedTests,
      totalAgents,
      averageScore,
      completionRate,
    };
  }, [session, results]);

  // 操作处理
  const handleStart = async () => {
    if (!session) return;
    await startSession(session.id);
  };

  const handleCancel = async () => {
    if (!session) return;
    Modal.confirm({
      title: "确认取消评测",
      content: "确定要取消当前的评测会话吗？已完成的结果将保留。",
      okText: "确定",
      cancelText: "取消",
      onOk: () => cancelSession(session.id),
    });
  };

  const handleRefresh = async () => {
    if (!session) return;
    await Promise.all([refreshSession(session.id), refreshResults(session.id)]);
  };

  // 移除handleViewResult方法，直接展示结果

  const handleExportResults = () => {
    if (!results || results.length === 0) {
      message.warning("暂无可导出的结果");
      return;
    }

    try {
      // 直接导出原始数据，保持完整结构
      const exportData = {
        session: session,
        results: results,
        export_metadata: {
          export_time: new Date().toISOString(),
          total_results: results.length,
        },
      };

      // 生成文件名
      const timestamp = new Date()
        .toISOString()
        .slice(0, 19)
        .replace(/:/g, "-");
      const filename = `evaluation_results_${session?.name || "unknown"}_${timestamp}.json`;

      // 创建并下载文件
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      message.success(`评测结果已导出: ${filename}`);
    } catch (error) {
      console.error("导出失败:", error);
      message.error("导出失败，请重试");
    }
  };

  const handleShowJson = () => {
    if (!results || results.length === 0) {
      message.warning("暂无可显示的结果");
      return;
    }

    // 准备导出数据 - 直接使用原始数据，不进行字段映射
    const exportData = {
      session: session,
      results: results,
    };

    showJson(exportData);
  };

  // 状态颜色映射
  const getStatusColor = (status: EvaluationStatus) => {
    switch (status) {
      case "pending":
        return "default";
      case "running":
        return "processing";
      case "completed":
        return "success";
      case "failed":
        return "error";
      case "cancelled":
        return "warning";
      default:
        return "default";
    }
  };

  // 状态图标映射
  const getStatusIcon = (status: EvaluationStatus) => {
    switch (status) {
      case "pending":
        return <ClockCircleOutlined />;
      case "running":
        return <FireOutlined />;
      case "completed":
        return <CheckCircleOutlined />;
      case "failed":
        return <ExclamationCircleOutlined />;
      case "cancelled":
        return <StopOutlined />;
      default:
        return <ClockCircleOutlined />;
    }
  };

  if (!session) {
    return (
      <Card title="评测监控">
        <Empty
          description="请先创建评测会话"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    );
  }

  return (
    <div className="evaluation-monitor">
      {/* 会话状态卡片 */}
      <Card
        title={
          <Space>
            <RobotOutlined />
            评测监控
            <Tag
              color={getStatusColor(session.status)}
              icon={getStatusIcon(session.status)}
            >
              {session.status === "pending" && "等待中"}
              {session.status === "running" && "运行中"}
              {session.status === "completed" && "已完成"}
              {session.status === "failed" && "失败"}
              {session.status === "cancelled" && "已取消"}
            </Tag>
            {isWebSocketConnected && <Badge status="success" text="实时连接" />}
          </Space>
        }
        extra={
          showControls && (
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
                loading={loading}
              >
                刷新
              </Button>
              {session.status === "pending" && (
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={handleStart}
                  loading={loading}
                >
                  开始评测
                </Button>
              )}
              {session.status === "running" && (
                <Button
                  danger
                  icon={<StopOutlined />}
                  onClick={handleCancel}
                  loading={loading}
                >
                  取消评测
                </Button>
              )}
              {results.length > 0 && (
                <>
                  <Button
                    icon={<DownloadOutlined />}
                    onClick={handleExportResults}
                  >
                    导出结果
                  </Button>
                  <Button icon={<RobotOutlined />} onClick={handleShowJson}>
                    查看JSON
                  </Button>
                </>
              )}
            </Space>
          )
        }
      >
        {/* 会话信息 */}
        <Descriptions column={2} size="small" style={{ marginBottom: 16 }}>
          <Descriptions.Item label="会话名称">{session.name}</Descriptions.Item>
          <Descriptions.Item label="创建时间 (UTC)">
            {formatUtcTimeRaw(session.created_at)}
          </Descriptions.Item>
          <Descriptions.Item label="测试问题">
            {session.config?.questions?.length || 0} 个
          </Descriptions.Item>
          <Descriptions.Item label="测试智能体">
            {session.config?.agents?.length || 0} 个
          </Descriptions.Item>
        </Descriptions>

        {/* 错误提示 */}
        {error && (
          <Alert
            message="监控错误"
            description={error}
            type="error"
            closable
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 进度统计 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Statistic
              title="总体进度"
              value={statistics.completionRate * 100}
              precision={1}
              suffix="%"
            />
            <Progress
              percent={statistics.completionRate * 100}
              size="small"
              status={session.status === "running" ? "active" : "normal"}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="已完成测试"
              value={statistics.completedTests}
              suffix={`/ ${statistics.totalTests}`}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="平均分数"
              value={statistics.averageScore}
              precision={1}
              suffix="/ 10"
              valueStyle={{
                color:
                  statistics.averageScore >= 7
                    ? "#52c41a"
                    : statistics.averageScore >= 5
                      ? "#faad14"
                      : "#ff4d4f",
              }}
            />
          </Col>
          <Col span={6}>
            <Statistic title="评测结果" value={results.length} suffix="个" />
          </Col>
        </Row>
      </Card>

      {/* 评测结果展示 */}
      {results.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <MultiAgentChatDisplay
            session={session}
            results={results}
            loading={loading}
            showControls={true}
          />
        </div>
      )}

      {/* JSON数据展示模态框 */}
      <JsonDisplayModal
        open={jsonModalVisible}
        onClose={hideJson}
        title="评测结果JSON数据"
        jsonData={jsonData}
      />
    </div>
  );
};
