/**
 * 多角色对话记录展示组件
 * 支持多个智能体的对话记录展示，包含全部展开/收起功能
 */

import React, { useState, useMemo } from "react";
import {
  Card,
  Collapse,
  Button,
  Typography,
  Avatar,
  Tag,
  Rate,
  Progress,
  Row,
  Col,
  Empty,
  Spin,
  Tooltip,
  Modal,
} from "antd";
import {
  ExpandOutlined,
  CompressOutlined,
  RobotOutlined,
  UserOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import type { EvaluationSession, EvaluationResult } from "../../types";

const { Text, Paragraph } = Typography;

interface MultiAgentChatDisplayProps {
  session: EvaluationSession;
  results: EvaluationResult[];
  loading?: boolean;
  showControls?: boolean;
}

interface AgentResultGroup {
  agentId: string;
  agentName: string;
  results: EvaluationResult[];
  completedCount: number;
  averageScore: number;
  bestScore: number;
  worstScore: number;
}

export const MultiAgentChatDisplay: React.FC<MultiAgentChatDisplayProps> = ({
  session,
  results,
  loading = false,
  showControls = true,
}) => {
  // 展开/收起状态
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [isAllExpanded, setIsAllExpanded] = useState(false);

  // 按智能体分组结果
  const agentGroups = useMemo(() => {
    if (!results || results.length === 0) return [];

    const groups = results.reduce(
      (acc, result) => {
        const agentId = result.agent_id;
        const agentName = result.agent_name || `角色 ${agentId.slice(0, 8)}`;

        if (!acc[agentId]) {
          acc[agentId] = {
            agentId,
            agentName,
            results: [],
            completedCount: 0,
            averageScore: 0,
            bestScore: 0,
            worstScore: 10,
          };
        }

        acc[agentId].results.push(result);

        if (result.is_success) {
          acc[agentId].completedCount++;
        }

        return acc;
      },
      {} as Record<string, AgentResultGroup>,
    );

    // 计算统计信息
    Object.values(groups).forEach((group) => {
      const validScores = group.results
        .filter((r) => r.overall_score != null)
        .map((r) => r.overall_score!);

      if (validScores.length > 0) {
        group.averageScore =
          validScores.reduce((sum, score) => sum + score, 0) /
          validScores.length;
        group.bestScore = Math.max(...validScores);
        group.worstScore = Math.min(...validScores);
      }

      // 按问题索引排序
      group.results.sort(
        (a, b) => (a.question_index ?? 0) - (b.question_index ?? 0),
      );
    });

    return Object.values(groups).sort((a, b) =>
      a.agentName.localeCompare(b.agentName),
    );
  }, [results]);

  // 处理全部展开/收起
  const handleExpandAll = () => {
    if (isAllExpanded) {
      setExpandedKeys([]);
      setIsAllExpanded(false);
    } else {
      const allKeys = agentGroups.map((group) => group.agentId);
      setExpandedKeys(allKeys);
      setIsAllExpanded(true);
    }
  };

  // 处理单个面板的展开/收起
  const handleCollapseChange = (keys: string | string[]) => {
    const keyArray = Array.isArray(keys) ? keys : [keys];
    setExpandedKeys(keyArray);
    setIsAllExpanded(
      keyArray.length === agentGroups.length && agentGroups.length > 0,
    );
  };

  // 获取状态图标
  const getStatusIcon = (result: EvaluationResult) => {
    if (result.is_success) {
      return <CheckCircleOutlined style={{ color: "#52c41a" }} />;
    } else {
      return <ExclamationCircleOutlined style={{ color: "#ff4d4f" }} />;
    }
  };

  // 显示评分详情模态框
  const showScoringDetail = (result: EvaluationResult) => {
    Modal.info({
      title: `评分详情 - ${result.agent_name || "角色"}`,
      width: 600,
      content: (
        <div>
          {/* 评分总览 */}
          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <Text strong>总分:</Text>
              <div style={{ display: "flex", alignItems: "center" }}>
                <Rate
                  disabled
                  value={result.overall_score ? result.overall_score / 2 : 0}
                  style={{ fontSize: "16px" }}
                />
                <Text
                  strong
                  style={{
                    marginLeft: "8px",
                    fontSize: "18px",
                    color:
                      (result.overall_score || 0) >= 7
                        ? "#52c41a"
                        : (result.overall_score || 0) >= 5
                          ? "#faad14"
                          : "#ff4d4f",
                  }}
                >
                  {result.overall_score
                    ? result.overall_score.toFixed(1)
                    : "0.0"}
                  /10
                </Text>
              </div>
            </div>
          </div>

          {/* 详细评分 */}
          {result.detailed_scores &&
            Object.keys(result.detailed_scores).length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <Text strong style={{ display: "block", marginBottom: 8 }}>
                  详细评分:
                </Text>
                {Object.entries(result.detailed_scores).map(
                  ([dimension, score]) => (
                    <div
                      key={dimension}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: 8,
                      }}
                    >
                      <Text>{dimension}</Text>
                      <div style={{ display: "flex", alignItems: "center" }}>
                        {(() => {
                          const scoreValue =
                            typeof score === "number" ? score : 0;
                          return (
                            <>
                              <Rate
                                disabled
                                value={scoreValue}
                                count={10}
                                style={{ fontSize: "12px" }}
                              />
                              <Text
                                style={{
                                  marginLeft: 8,
                                  color:
                                    scoreValue >= 7
                                      ? "#52c41a"
                                      : scoreValue >= 5
                                        ? "#faad14"
                                        : "#ff4d4f",
                                }}
                              >
                                {scoreValue.toFixed(1)}
                              </Text>
                            </>
                          );
                        })()}
                      </div>
                    </div>
                  ),
                )}
              </div>
            )}

          {/* 评分理由 */}
          {result.scoring_reason && (
            <div>
              <Text strong style={{ display: "block", marginBottom: 8 }}>
                评分理由:
              </Text>
              <div
                style={{
                  backgroundColor: "#f5f5f5",
                  padding: "12px",
                  borderRadius: "8px",
                  border: "1px solid #e8e8e8",
                  whiteSpace: "pre-wrap",
                  lineHeight: "1.6",
                }}
              >
                {result.scoring_reason}
              </div>
            </div>
          )}

          {/* 技术信息 */}
          <div
            style={{
              marginTop: 16,
              paddingTop: 16,
              borderTop: "1px solid #e8e8e8",
            }}
          >
            <Text type="secondary" style={{ fontSize: "12px" }}>
              评分模型: {result.scoring_model_used || "未知"} | 响应时间:{" "}
              {result.response_time
                ? `${result.response_time.toFixed(2)}s`
                : "未知"}
            </Text>
          </div>
        </div>
      ),
      okText: "关闭",
    });
  };

  // 渲染对话气泡
  const renderChatBubbles = (result: EvaluationResult) => {
    return (
      <div style={{ marginBottom: "24px" }}>
        {/* 问题气泡 - 用户发送 */}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            marginBottom: "16px",
          }}
        >
          <div
            style={{ display: "flex", alignItems: "flex-end", maxWidth: "70%" }}
          >
            <div
              style={{
                backgroundColor: "#1890ff",
                color: "white",
                padding: "12px 16px",
                borderRadius: "18px 18px 4px 18px",
                fontSize: "14px",
                lineHeight: "1.4",
                boxShadow: "0 2px 8px rgba(24, 144, 255, 0.15)",
                wordBreak: "break-word",
              }}
            >
              <div
                style={{
                  fontWeight: "bold",
                  marginBottom: "4px",
                  fontSize: "12px",
                  opacity: 0.9,
                }}
              >
                问题 {(result.question_index ?? 0) + 1}
              </div>
              {result.question}
            </div>
            <Avatar
              size={32}
              icon={<UserOutlined />}
              style={{
                marginLeft: "8px",
                backgroundColor: "#1890ff",
                flexShrink: 0,
              }}
            />
          </div>
        </div>

        {/* 回答气泡 - AI回复 */}
        <div style={{ display: "flex", justifyContent: "flex-start" }}>
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              maxWidth: "75%",
            }}
          >
            <Avatar
              size={32}
              icon={<RobotOutlined />}
              style={{
                marginRight: "8px",
                backgroundColor: result.is_success ? "#52c41a" : "#ff4d4f",
                flexShrink: 0,
              }}
            />
            <div style={{ flex: 1 }}>
              <div
                style={{
                  backgroundColor: "white",
                  color: "#333",
                  padding: "12px 16px",
                  borderRadius: "18px 18px 18px 4px",
                  fontSize: "14px",
                  lineHeight: "1.4",
                  boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
                  border: result.is_success
                    ? "1px solid #e8e8e8"
                    : "1px solid #ff4d4f",
                  wordBreak: "break-word",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "8px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center" }}>
                    <Text strong style={{ fontSize: "12px", color: "#666" }}>
                      {result.agent_name || "角色"}
                    </Text>
                    {getStatusIcon(result)}
                    {result.response_time && (
                      <Text
                        style={{
                          fontSize: "11px",
                          color: "#999",
                          marginLeft: "8px",
                        }}
                      >
                        {result.response_time.toFixed(2)}s
                      </Text>
                    )}
                  </div>

                  {/* 评分显示 */}
                  <div style={{ display: "flex", alignItems: "center" }}>
                    {result.overall_score && (
                      <>
                        <Rate
                          disabled
                          value={result.overall_score / 2}
                          style={{ fontSize: "12px" }}
                        />
                        <Text
                          strong
                          style={{
                            marginLeft: "8px",
                            color:
                              result.overall_score >= 7
                                ? "#52c41a"
                                : result.overall_score >= 5
                                  ? "#faad14"
                                  : "#ff4d4f",
                          }}
                        >
                          {result.overall_score.toFixed(1)}/10
                        </Text>
                      </>
                    )}

                    {/* 评分详情按钮 - 显示评分理由等详细信息 */}
                    {result.overall_score && (
                      <Tooltip title="查看评分详情">
                        <Button
                          type="text"
                          size="small"
                          icon={<EyeOutlined />}
                          onClick={() => showScoringDetail(result)}
                          style={{ marginLeft: "8px" }}
                        />
                      </Tooltip>
                    )}
                  </div>
                </div>

                <div>
                  {result.is_success ? (
                    <div>
                      <Paragraph style={{ margin: 0, whiteSpace: "pre-wrap" }}>
                        {result.agent_response || "等待回答..."}
                      </Paragraph>
                      {/* MessageToImageIcon requires messageId and agentId, which are not available here */}
                    </div>
                  ) : (
                    <Text type="danger">
                      {result.error_message ||
                        result.agent_response ||
                        "回答失败"}
                    </Text>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: "center", padding: "40px" }}>
          <Spin size="large" tip="加载对话记录中..." />
        </div>
      </Card>
    );
  }

  if (!agentGroups.length) {
    return (
      <Card>
        <Empty
          description="暂无对话记录"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    );
  }

  return (
    <Card
      title="多角色对话记录"
      extra={
        showControls &&
        agentGroups.length > 0 && (
          <Button
            type="text"
            size="small"
            icon={isAllExpanded ? <CompressOutlined /> : <ExpandOutlined />}
            onClick={handleExpandAll}
            style={{ color: "#1890ff" }}
          >
            {isAllExpanded ? "全部收起" : "全部展开"}
          </Button>
        )
      }
    >
      <Row gutter={16}>
        {agentGroups.map((group) => {
          const totalQuestions = session.questions?.length || 0;
          const completionRate =
            totalQuestions > 0 ? group.completedCount / totalQuestions : 0;

          const collapseItems = [
            {
              key: group.agentId,
              label: (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center" }}>
                    <Avatar
                      size={24}
                      style={{ marginRight: 8, backgroundColor: "#1890ff" }}
                    >
                      {group.agentName[0] || "A"}
                    </Avatar>
                    <span>{group.agentName}</span>
                    {group.averageScore > 0 && (
                      <div
                        style={{
                          marginLeft: 12,
                          display: "flex",
                          alignItems: "center",
                        }}
                      >
                        <Text
                          strong
                          style={{
                            fontSize: "16px",
                            color:
                              group.averageScore >= 8
                                ? "#52c41a"
                                : group.averageScore >= 6
                                  ? "#fa8c16"
                                  : "#ff4d4f",
                          }}
                        >
                          平均分: {group.averageScore.toFixed(1)}/10
                        </Text>
                        <Rate
                          disabled
                          value={group.averageScore / 2}
                          style={{ fontSize: "12px", marginLeft: 8 }}
                        />
                      </div>
                    )}
                  </div>
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 8 }}
                  >
                    {group.averageScore > 0 && (
                      <Tag
                        color={
                          group.averageScore >= 8
                            ? "green"
                            : group.averageScore >= 6
                              ? "orange"
                              : "red"
                        }
                        style={{ fontSize: "12px" }}
                      >
                        {group.averageScore >= 8
                          ? "优秀"
                          : group.averageScore >= 6
                            ? "良好"
                            : "需改进"}
                      </Tag>
                    )}
                    <Tag
                      color={
                        group.completedCount === totalQuestions
                          ? "green"
                          : "orange"
                      }
                    >
                      {group.completedCount}/{totalQuestions} 问题已完成
                    </Tag>
                    <div style={{ minWidth: "80px" }}>
                      <Progress
                        percent={Math.round(completionRate * 100)}
                        size="small"
                        showInfo={false}
                        strokeColor={
                          completionRate === 1 ? "#52c41a" : "#1890ff"
                        }
                      />
                    </div>
                  </div>
                </div>
              ),
              children: (
                <div
                  style={{
                    maxHeight: "600px",
                    overflowY: "auto",
                    padding: "12px",
                    backgroundColor: "#f8f9fa",
                    borderRadius: "8px",
                  }}
                >
                  {group.results.map((result) => (
                    <div key={result.id}>{renderChatBubbles(result)}</div>
                  ))}
                </div>
              ),
            },
          ];

          return (
            <Col span={12} key={group.agentId} style={{ marginBottom: 16 }}>
              <Collapse
                items={collapseItems}
                activeKey={
                  expandedKeys.includes(group.agentId) ? [group.agentId] : []
                }
                onChange={(keys) => {
                  const keyArray = Array.isArray(keys) ? keys : [keys];
                  let newExpandedKeys = [...expandedKeys];

                  if (keyArray.includes(group.agentId)) {
                    // 展开当前面板
                    if (!newExpandedKeys.includes(group.agentId)) {
                      newExpandedKeys.push(group.agentId);
                    }
                  } else {
                    // 收起当前面板
                    newExpandedKeys = newExpandedKeys.filter(
                      (key) => key !== group.agentId,
                    );
                  }

                  handleCollapseChange(newExpandedKeys);
                }}
              />
            </Col>
          );
        })}
      </Row>
    </Card>
  );
};
