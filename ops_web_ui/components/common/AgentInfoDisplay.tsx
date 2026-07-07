/**
 * 智能体信息展示组件
 * 用于显示智能体的详细信息，包括基本信息、提示词配置、图片资源等
 */

import React from "react";
import { Card, Row, Col, Tag } from "antd";
import { CloseCircleOutlined } from "@ant-design/icons";
import type { Agent } from "../../types";
import { AvatarDisplay } from "./AvatarDisplay";
import { BackgroundWithCropOverlay } from "./BackgroundWithCropOverlay";
import ScoreSelector from "./ScoreSelector";
import { formatUtcTime } from "../../utils/dateUtils";

interface AgentInfoDisplayProps {
  agent: Agent;
  showImages?: boolean;
  showPrompts?: boolean;
  showLLMConfig?: boolean;
  compact?: boolean;
  onDeleteBackgroundImage?: (imageUrl: string) => void;
}

export const AgentInfoDisplay: React.FC<AgentInfoDisplayProps> = ({
  agent,
  showImages = true,
  showPrompts = true,
  showLLMConfig = true,
  compact = false,
  onDeleteBackgroundImage,
}) => {
  // 统一的图片样式
  const imageStyle = {
    width: "100%",
    maxWidth: 120,
    height: "auto",
    objectFit: "contain" as const, // 保持原始长宽比，完整显示图片
  };
  const renderBasicInfo = () => (
    <Card size="small" title="基本信息" style={{ marginBottom: 16 }}>
      <Row gutter={[16, 16]} align="middle">
        <Col span={compact ? 8 : 6} style={{ textAlign: "center" }}>
          <AvatarDisplay agent={agent} size={compact ? 60 : 80} />
          <div style={{ marginTop: 8 }}>
            <Tag color={agent.visibility === "PUBLIC" ? "green" : "orange"}>
              {agent.visibility === "PUBLIC" ? "公开" : "私有"}
            </Tag>
          </div>
        </Col>
        <Col span={compact ? 16 : 18}>
          <p>
            <strong>ID:</strong> {agent.id}
          </p>
          <p>
            <strong>名称:</strong> {agent.name}
          </p>
          <p>
            <strong>性别:</strong>{" "}
            {agent.gender === "MALE"
              ? "男"
              : agent.gender === "FEMALE"
                ? "女"
                : "其他"}
          </p>
          <p>
            <strong>简介:</strong> {agent.intro || "无"}
          </p>
          <p>
            <strong>开场白:</strong> {agent.opening || "无"}
          </p>
          <p>
            <strong>背景设定:</strong> {agent.scenario || "无"}
          </p>
          <p>
            <strong>创建时间 (UTC):</strong> {formatUtcTime(agent.created_at)}
          </p>
          <p>
            <strong>更新时间 (UTC):</strong> {formatUtcTime(agent.updated_at)}
          </p>
          <p>
            <strong>音色ID:</strong> {agent.voice_id || "未设置"}
          </p>
          <p>
            <strong>对话模型:</strong>{" "}
            {agent.llm_config?.model?.trim()
              ? agent.llm_config.model.trim()
              : "平台默认"}
          </p>
          <p>
            <strong>头像尺寸:</strong>{" "}
            {agent.avatar_size
              ? `${agent.avatar_size.width} × ${agent.avatar_size.height} 像素`
              : "未设置"}
          </p>
          <p>
            <strong>背景图尺寸:</strong>{" "}
            {agent.background_size
              ? `${agent.background_size.width} × ${agent.background_size.height} 像素`
              : "未设置"}
          </p>
          {agent.tags && agent.tags.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <strong>标签:</strong>
              <div
                style={{
                  marginTop: 4,
                  display: "flex",
                  gap: 4,
                  flexWrap: "wrap",
                }}
              >
                {agent.tags.map((tag, index) => (
                  <Tag key={index} color="geekblue">
                    {tag}
                  </Tag>
                ))}
              </div>
            </div>
          )}
          {agent.meta_data?.score && (
            <div style={{ marginTop: 8 }}>
              <strong>评分:</strong>
              <div style={{ marginTop: 4 }}>
                <ScoreSelector
                  value={agent.meta_data.score}
                  disabled={true}
                  mode="star"
                  showText={true}
                />
              </div>
            </div>
          )}
          {agent.meta_data?.comment && (
            <div style={{ marginTop: 8 }}>
              <strong>备注:</strong>
              <div
                style={{
                  marginTop: 4,
                  padding: 8,
                  backgroundColor: "#f5f5f5",
                  borderRadius: 4,
                  fontSize: "14px",
                  whiteSpace: "pre-wrap",
                }}
              >
                {agent.meta_data.comment}
              </div>
            </div>
          )}
        </Col>
      </Row>
    </Card>
  );

  const renderPrompts = () => {
    if (!showPrompts) return null;

    return (
      <Card size="small" title="提示词配置" style={{ marginBottom: 16 }}>
        <p>
          <strong>主提示词:</strong>
        </p>
        <div
          style={{
            background: "#f5f5f5",
            padding: 12,
            borderRadius: 6,
            maxHeight: compact ? 150 : 200,
            overflowY: "auto",
            whiteSpace: "pre-wrap",
            fontSize: "12px",
          }}
        >
          {agent.main_prompt || "无"}
        </div>
        <p style={{ marginTop: 16 }}>
          <strong>角色信息:</strong>
        </p>
        <div
          style={{
            background: "#f5f5f5",
            padding: 12,
            borderRadius: 6,
            maxHeight: compact ? 150 : 200,
            overflowY: "auto",
            whiteSpace: "pre-wrap",
            fontSize: "12px",
          }}
        >
          {agent.personality || "无"}
        </div>
        <p style={{ marginTop: 16 }}>
          <strong>聊天模式:</strong>
        </p>
        <div
          style={{
            background: "#f5f5f5",
            padding: 12,
            borderRadius: 6,
            maxHeight: compact ? 150 : 200,
            overflowY: "auto",
            whiteSpace: "pre-wrap",
            fontSize: "12px",
          }}
        >
          {agent.mode_prompt || "无"}
        </div>
      </Card>
    );
  };

  const renderImages = () => {
    if (!showImages) return null;

    return (
      <Card size="small" title="图片资源" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <p>
              <strong>头像:</strong>
            </p>
            {agent.avatar ? (
              <img src={agent.avatar} alt="avatar" style={imageStyle} />
            ) : (
              <span style={{ color: "#999" }}>无</span>
            )}
          </Col>
          <Col xs={24} md={8}>
            <p>
              <strong>背景图及截取头像效果:</strong>
            </p>
            <BackgroundWithCropOverlay
              agent={agent}
              style={imageStyle}
              showCropOverlay={true}
            />
          </Col>
          <Col xs={24} md={8}>
            <p>
              <strong>动态背景动图:</strong>
            </p>
            {agent.background_animated ? (
              <div
                style={{
                  width: "100%",
                  maxWidth: 220,
                  borderRadius: 8,
                  overflow: "hidden",
                  border: "1px solid #eee",
                  backgroundColor: "#000",
                }}
              >
                <img
                  key={agent.background_animated}
                  src={agent.background_animated}
                  alt="背景动图"
                  style={{
                    width: "100%",
                    display: "block",
                  }}
                />
                <div
                  style={{
                    padding: "6px 8px",
                    fontSize: 12,
                    color: "#666",
                    backgroundColor: "#fafafa",
                    borderTop: "1px solid #f0f0f0",
                  }}
                >
                  <a
                    href={agent.background_animated}
                    target="_blank"
                    rel="noreferrer"
                  >
                    在新标签页中打开
                  </a>
                </div>
              </div>
            ) : (
              <span style={{ color: "#999" }}>无</span>
            )}
          </Col>
        </Row>
        {agent.background_images && agent.background_images.length > 0 && (
          <>
            <p style={{ marginTop: 16 }}>
              <strong>背景图列表:</strong>
            </p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {agent.background_images.map((img, index) => (
                <div
                  key={index}
                  style={{
                    position: "relative",
                    display: "inline-block",
                  }}
                >
                  <img
                    src={img}
                    alt={`background-${index}`}
                    style={imageStyle}
                  />
                  {onDeleteBackgroundImage && (
                    <CloseCircleOutlined
                      onClick={() => onDeleteBackgroundImage(img)}
                      style={{
                        position: "absolute",
                        top: 4,
                        right: 4,
                        fontSize: 18,
                        color: "#ff4d4f",
                        backgroundColor: "white",
                        borderRadius: "50%",
                        cursor: "pointer",
                      }}
                    />
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </Card>
    );
  };

  const renderLLMConfig = () => {
    if (!showLLMConfig || !agent.llm_config) return null;

    return (
      <Card size="small" title="自定义模型配置">
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <p>
              <strong>模型:</strong> {agent.llm_config.model || "无"}
            </p>
            <p>
              <strong>温度:</strong> {agent.llm_config.temperature ?? "无"}
            </p>
            <p>
              <strong>最大令牌数:</strong> {agent.llm_config.max_tokens ?? "无"}
            </p>
          </Col>
          <Col span={12}>
            <p>
              <strong>Top P:</strong> {agent.llm_config.top_p ?? "无"}
            </p>
            <p>
              <strong>频率惩罚:</strong>{" "}
              {agent.llm_config.frequency_penalty ?? "无"}
            </p>
            <p>
              <strong>存在惩罚:</strong>{" "}
              {agent.llm_config.presence_penalty ?? "无"}
            </p>
          </Col>
        </Row>
      </Card>
    );
  };

  return (
    <div
      style={{
        maxHeight: compact ? 400 : 600,
        overflowY: "auto",
        padding: compact ? 8 : 16,
      }}
    >
      {renderBasicInfo()}
      {renderPrompts()}
      {renderImages()}
      {renderLLMConfig()}
    </div>
  );
};

export default AgentInfoDisplay;
