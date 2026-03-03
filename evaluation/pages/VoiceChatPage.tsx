/**
 * 实时语音通话页面
 * 提供与智能体的实时语音对话功能
 * CREATED_BY_AGENT
 */

import React, { useState, useEffect, useRef } from "react";
import {
  Layout,
  Card,
  Button,
  List,
  Avatar,
  Space,
  Typography,
  Row,
  Col,
  Empty,
  message,
  Tag,
} from "antd";
import {
  PhoneOutlined,
  AudioOutlined,
  AudioMutedOutlined,
  UserOutlined,
  ClockCircleOutlined,
  WifiOutlined,
  LoadingOutlined,
  DashboardOutlined,
} from "@ant-design/icons";
import { useLiveChat, Transcript } from "../hooks/useLiveChat";
import type { Agent } from "../types";
import { AvatarDisplay } from "../components/common/AvatarDisplay";
import { SingleAgentSelectorPanel } from "../components/common/SingleAgentSelectorPanel";
import { formatUtcTimeOnly } from "../utils/dateUtils";

const { Content } = Layout;
const { Text, Paragraph, Title } = Typography;

const STATUS_LABELS: Record<string, { text: string; color: string }> = {
  idle: { text: "未连接", color: "default" },
  connecting: { text: "连接中...", color: "processing" },
  connected: { text: "已连接", color: "success" },
  speaking: { text: "AI 说话中", color: "purple" },
  listening: { text: "聆听中", color: "blue" },
  disconnected: { text: "已断开", color: "default" },
  error: { text: "连接错误", color: "error" },
};

export interface VoiceChatPageProps {
  /** 通话结束后可调用以跳转到「用户每日消息」查看录音 */
  onNavigateToUserDailyMessages?: () => void;
}

export const VoiceChatPage: React.FC<VoiceChatPageProps> = ({
  onNavigateToUserDailyMessages,
}) => {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const transcriptsEndRef = useRef<HTMLDivElement>(null);

  const {
    status,
    isRecording,
    isMuted,
    transcripts,
    error,
    remainingDuration,
    elapsedTime,
    latencyMetrics,
    startCall,
    endCall,
    toggleMute,
    clearTranscripts,
    clearError,
  } = useLiveChat();

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const getDurationColor = (remaining: number | null): string => {
    if (remaining === null) return "rgba(255,255,255,0.9)";
    if (remaining <= 10) return "#ff4d4f";
    if (remaining <= 30) return "#faad14";
    return "rgba(255,255,255,0.9)";
  };

  useEffect(() => {
    transcriptsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts]);

  useEffect(() => {
    if (error) {
      message.error(`${error.code}: ${error.message}`);
    }
  }, [error]);

  const handleSelectAgent = (agent: Agent) => {
    if (status !== "idle" && status !== "disconnected" && status !== "error") {
      message.warning("请先结束当前通话");
      return;
    }
    setSelectedAgent(agent);
    clearTranscripts();
    clearError();
  };

  const handleStartCall = async () => {
    if (!selectedAgent) {
      message.warning("请先选择一个智能体");
      return;
    }

    try {
      await startCall(selectedAgent.id);
      message.success("通话已开始");
    } catch (err) {
      message.error("启动通话失败");
    }
  };

  const handleEndCall = () => {
    endCall();
    message.info("通话已结束");
  };

  const handleToggleMute = () => {
    toggleMute();
    message.info(isMuted ? "已取消静音" : "已静音");
  };

  const isInCall =
    status === "connected" || status === "speaking" || status === "listening";

  const statusInfo = STATUS_LABELS[status] || STATUS_LABELS.idle;

  return (
    <Layout
      className="voice-chat-page"
      style={{ height: "100vh", overflow: "hidden" }}
    >
      <Content
        style={{
          padding: "24px",
          background: "#f0f2f5",
          height: "100%",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Row gutter={24} style={{ flex: 1, minHeight: 0 }}>
          {/* 智能体选择侧栏 */}
          <Col span={6} style={{ height: "100%" }}>
            <SingleAgentSelectorPanel
              selectedAgentId={selectedAgent?.id}
              onSelectAgent={handleSelectAgent}
            />
          </Col>

          {/* 通话主区域 */}
          <Col span={18} style={{ height: "100%" }}>
            {selectedAgent ? (
              <Card
                title={
                  <Space>
                    <AvatarDisplay agent={selectedAgent} size={32} />
                    <div>
                      <Text strong>{selectedAgent.name}</Text>
                      <div>
                        <Tag color={statusInfo.color}>
                          {status === "connecting" && (
                            <LoadingOutlined style={{ marginRight: 4 }} />
                          )}
                          {status === "connected" && (
                            <WifiOutlined style={{ marginRight: 4 }} />
                          )}
                          {statusInfo.text}
                        </Tag>
                      </div>
                    </div>
                  </Space>
                }
                style={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                }}
                styles={{
                  body: {
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    padding: 0,
                    overflow: "hidden",
                  },
                }}
              >
                {/* 角色信息和通话控制区 */}
                <div
                  style={{
                    padding: "24px",
                    textAlign: "center",
                    background:
                      "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                    color: "#fff",
                  }}
                >
                  <AvatarDisplay
                    agent={selectedAgent}
                    size={120}
                    style={{
                      border: "4px solid rgba(255,255,255,0.3)",
                      marginBottom: 16,
                    }}
                  />
                  <Title level={3} style={{ color: "#fff", margin: 0 }}>
                    {selectedAgent.name}
                  </Title>
                  <Paragraph
                    style={{
                      color: "rgba(255,255,255,0.8)",
                      marginTop: 8,
                      marginBottom: 24,
                    }}
                  >
                    {selectedAgent.intro}
                  </Paragraph>

                  {/* 通话控制按钮 */}
                  <Space size="large">
                    {!isInCall ? (
                      <Button
                        type="primary"
                        size="large"
                        icon={<PhoneOutlined />}
                        onClick={handleStartCall}
                        loading={status === "connecting"}
                        style={{
                          height: 60,
                          width: 180,
                          fontSize: 18,
                          borderRadius: 30,
                          background: "#52c41a",
                          borderColor: "#52c41a",
                        }}
                      >
                        开始通话
                      </Button>
                    ) : (
                      <>
                        <Button
                          size="large"
                          icon={
                            isMuted ? <AudioMutedOutlined /> : <AudioOutlined />
                          }
                          onClick={handleToggleMute}
                          style={{
                            height: 60,
                            width: 60,
                            borderRadius: 30,
                            background: isMuted
                              ? "rgba(255,255,255,0.2)"
                              : "#fff",
                            color: isMuted ? "#fff" : "#1890ff",
                          }}
                        />
                        <Button
                          type="primary"
                          danger
                          size="large"
                          icon={
                            <PhoneOutlined
                              style={{ transform: "rotate(135deg)" }}
                            />
                          }
                          onClick={handleEndCall}
                          style={{
                            height: 60,
                            width: 180,
                            fontSize: 18,
                            borderRadius: 30,
                          }}
                        >
                          结束通话
                        </Button>
                      </>
                    )}
                  </Space>

                  {/* 通话时长显示 */}
                  {isInCall && (
                    <div style={{ marginTop: 16, marginBottom: 8 }}>
                      <Space size="large">
                        <div>
                          <Text
                            style={{
                              color: "rgba(255,255,255,0.7)",
                              fontSize: 12,
                            }}
                          >
                            已通话
                          </Text>
                          <div
                            style={{
                              fontSize: 24,
                              fontWeight: "bold",
                              color: "rgba(255,255,255,0.9)",
                              fontFamily: "monospace",
                            }}
                          >
                            {formatDuration(elapsedTime)}
                          </div>
                        </div>
                        {remainingDuration !== null && (
                          <div>
                            <Text
                              style={{
                                color: "rgba(255,255,255,0.7)",
                                fontSize: 12,
                              }}
                            >
                              剩余时间
                            </Text>
                            <div
                              style={{
                                fontSize: 24,
                                fontWeight: "bold",
                                color: getDurationColor(remainingDuration),
                                fontFamily: "monospace",
                                animation:
                                  remainingDuration <= 10
                                    ? "blink 1s infinite"
                                    : "none",
                              }}
                            >
                              <ClockCircleOutlined
                                style={{ marginRight: 4, fontSize: 18 }}
                              />
                              {formatDuration(remainingDuration)}
                            </div>
                          </div>
                        )}
                      </Space>
                    </div>
                  )}

                  {/* 录音状态指示 */}
                  {isRecording && !isMuted && (
                    <div style={{ marginTop: 8 }}>
                      <Space>
                        <span
                          style={{
                            display: "inline-block",
                            width: 12,
                            height: 12,
                            borderRadius: "50%",
                            background: "#f5222d",
                            animation: "pulse 1.5s infinite",
                          }}
                        />
                        <Text style={{ color: "rgba(255,255,255,0.9)" }}>
                          正在录音...
                        </Text>
                      </Space>
                    </div>
                  )}

                  {/* 延迟指标展示 */}
                  {(latencyMetrics.connectLatencyMs !== undefined ||
                    latencyMetrics.firstResponseAfterSilenceMs !== undefined ||
                    latencyMetrics.turnLatenciesMs !== undefined) && (
                    <div
                      style={{
                        marginTop: 16,
                        padding: "12px 16px",
                        background: "rgba(255,255,255,0.15)",
                        borderRadius: 8,
                        display: "inline-block",
                      }}
                    >
                      <Space size="middle" wrap>
                        <Text
                          style={{
                            color: "rgba(255,255,255,0.9)",
                            fontWeight: 500,
                          }}
                        >
                          <DashboardOutlined style={{ marginRight: 4 }} />
                          延迟指标
                        </Text>
                        {latencyMetrics.connectLatencyMs !== undefined && (
                          <Tag color="blue">
                            连接: {latencyMetrics.connectLatencyMs}ms
                          </Tag>
                        )}
                        {latencyMetrics.firstResponseAfterSilenceMs !==
                          undefined && (
                          <Tag color="green">
                            静默后首响应:{" "}
                            {latencyMetrics.firstResponseAfterSilenceMs}ms
                          </Tag>
                        )}
                        {latencyMetrics.avgTurnLatencyMs !== undefined && (
                          <Tag color="purple">
                            平均轮次: {latencyMetrics.avgTurnLatencyMs}ms
                          </Tag>
                        )}
                        {latencyMetrics.turnLatenciesMs &&
                          latencyMetrics.turnLatenciesMs.length > 0 && (
                            <Tag color="orange">
                              轮次:{" "}
                              {latencyMetrics.turnLatenciesMs
                                .slice(-3)
                                .join(" / ")}
                              ms
                            </Tag>
                          )}
                      </Space>
                    </div>
                  )}

                  {/* 通话结束后提示：可前往用户每日消息查看录音 */}
                  {status === "disconnected" &&
                    onNavigateToUserDailyMessages && (
                      <div
                        style={{
                          marginTop: 16,
                          padding: "12px 16px",
                          background: "rgba(255,255,255,0.2)",
                          borderRadius: 8,
                          textAlign: "center",
                        }}
                      >
                        <Text
                          style={{
                            color: "rgba(255,255,255,0.95)",
                            marginRight: 8,
                          }}
                        >
                          Call saved. View or play the recording in User Daily
                          Messages.
                        </Text>
                        <Button
                          type="primary"
                          size="small"
                          onClick={onNavigateToUserDailyMessages}
                          style={{
                            background: "#fff",
                            color: "#667eea",
                            borderColor: "#fff",
                          }}
                        >
                          View recording
                        </Button>
                      </div>
                    )}
                </div>

                {/* 转录文本显示区域 */}
                <div
                  style={{
                    flex: 1,
                    overflowY: "auto",
                    padding: "16px",
                    background: "#fafafa",
                  }}
                >
                  {transcripts.length === 0 ? (
                    <Empty
                      description="开始通话后，对话内容将显示在这里"
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      style={{ marginTop: 60 }}
                    />
                  ) : (
                    <List
                      dataSource={transcripts}
                      renderItem={(transcript: Transcript) => (
                        <List.Item
                          style={{
                            border: "none",
                            padding: "8px 0",
                            justifyContent:
                              transcript.role === "user"
                                ? "flex-end"
                                : "flex-start",
                          }}
                        >
                          <div
                            style={{
                              maxWidth: "80%",
                              display: "flex",
                              flexDirection:
                                transcript.role === "user"
                                  ? "row-reverse"
                                  : "row",
                              alignItems: "flex-start",
                              gap: "8px",
                            }}
                          >
                            {transcript.role === "user" ? (
                              <Avatar
                                size="small"
                                icon={<UserOutlined />}
                                style={{ backgroundColor: "#1890ff" }}
                              />
                            ) : (
                              <AvatarDisplay agent={selectedAgent} size={24} />
                            )}
                            <div
                              style={{
                                backgroundColor:
                                  transcript.role === "user"
                                    ? "#1890ff"
                                    : "#fff",
                                color:
                                  transcript.role === "user" ? "#fff" : "#000",
                                padding: "10px 14px",
                                borderRadius: "16px",
                                boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
                              }}
                            >
                              <Paragraph
                                style={{
                                  margin: 0,
                                  color:
                                    transcript.role === "user"
                                      ? "#fff"
                                      : "#000",
                                }}
                              >
                                {transcript.text}
                              </Paragraph>
                              <div
                                style={{
                                  fontSize: "10px",
                                  opacity: 0.7,
                                  marginTop: "4px",
                                  textAlign:
                                    transcript.role === "user"
                                      ? "right"
                                      : "left",
                                }}
                              >
                                <ClockCircleOutlined
                                  style={{ marginRight: "2px" }}
                                />
                                {formatUtcTimeOnly(transcript.timestamp)}
                              </div>
                            </div>
                          </div>
                        </List.Item>
                      )}
                    />
                  )}
                  <div ref={transcriptsEndRef} />
                </div>
              </Card>
            ) : (
              <Card style={{ height: "100%" }}>
                <div style={{ textAlign: "center", padding: "100px 0" }}>
                  <Empty
                    description="请选择一个智能体开始语音通话"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                </div>
              </Card>
            )}
          </Col>
        </Row>
      </Content>

      {/* 动画样式 */}
      <style>{`
        @keyframes pulse {
          0% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.5;
            transform: scale(1.2);
          }
          100% {
            opacity: 1;
            transform: scale(1);
          }
        }
        @keyframes blink {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }
      `}</style>
    </Layout>
  );
};
