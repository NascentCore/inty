/**
 * 生成图片详情弹窗（支持完整 metadata 展示）
 * CREATED_BY_AGENT
 */
import React, { useEffect, useMemo, useState } from "react";
import { Card, Image, List, Modal, Space, Spin, Tag, Typography } from "antd";
import { PictureOutlined } from "@ant-design/icons";
import { formatUtcTimeRaw } from "../../utils/dateUtils";
import type { GeneratedImageDetail } from "../../utils/generatedImageDetail";
import { reportApi } from "../../services/api";
import type { ReportItem } from "../../types";
import { buildImageFeedbackTargetId } from "../../utils/imageFeedbackReport";

const { Text, Paragraph, Title } = Typography;

interface GeneratedImageDetailModalProps {
  open: boolean;
  onClose: () => void;
  detail: GeneratedImageDetail | null;
  title?: string;
}

function getGenerationModeLabel(detail: GeneratedImageDetail): string | null {
  if (
    detail.isMatchedFallback ||
    detail.generationMode === "fallback_matched_image"
  ) {
    return "兜底生图（命中历史图）";
  }
  if (detail.generationMode === "fresh_generation") {
    return "新生成";
  }
  return null;
}

function formatDateTime(dateTime: string | null): string {
  if (!dateTime) {
    return "时间未知";
  }
  return `${formatUtcTimeRaw(dateTime, "YYYY-MM-DD HH:mm:ss")} (UTC)`;
}

function formatGenerationTimeMs(
  generationTimeMs: number | null,
): string | null {
  if (generationTimeMs === null) {
    return null;
  }
  return `${(generationTimeMs / 1000).toFixed(2)}s (${Math.round(generationTimeMs)}ms)`;
}

function parseFeedbackVote(
  description: string | null,
): "like" | "dislike" | null {
  if (!description) {
    return null;
  }
  const matched = description.match(/\[vote=(like|dislike)\]/);
  if (!matched) {
    return null;
  }
  return matched[1] as "like" | "dislike";
}

function parseFeedbackContent(description: string | null): string {
  if (!description) {
    return "（无文字反馈）";
  }
  const cleanedDescription = description
    .replace("[IMAGE_FEEDBACK]", "")
    .replace(/\[vote=(like|dislike)\]/, "")
    .replace(/\[reason_codes=[A-Z0-9_,]+\]/, "")
    .trim();
  return cleanedDescription || "（无文字反馈）";
}

export const GeneratedImageDetailModal: React.FC<
  GeneratedImageDetailModalProps
> = ({ open, onClose, detail, title = "图片详情" }) => {
  const [feedbackItems, setFeedbackItems] = useState<ReportItem[]>([]);
  const [feedbackLoading, setFeedbackLoading] = useState(false);

  useEffect(() => {
    if (!open || !detail?.imageUrl) {
      setFeedbackItems([]);
      return;
    }
    const targetImageUrl = detail.imageUrl;
    const targetId = buildImageFeedbackTargetId(targetImageUrl);
    let cancelled = false;
    setFeedbackLoading(true);
    reportApi
      .list({
        report_type: "FEEDBACK",
        target_id: targetId,
        order_by: "created_at_desc",
        limit: 20,
      })
      .then((result) => {
        if (cancelled) {
          return;
        }
        const matchedItems = result.items.filter((item) => {
          if (item.target_id === targetId) {
            return true;
          }
          return item.image_urls.includes(targetImageUrl);
        });
        setFeedbackItems(matchedItems);
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        console.error("Failed to load image feedbacks:", error);
        setFeedbackItems([]);
      })
      .finally(() => {
        if (!cancelled) {
          setFeedbackLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [detail?.imageUrl, open]);

  const metadataJson = useMemo(() => {
    if (!detail || Object.keys(detail.metaData).length === 0) {
      return "暂无 metadata";
    }
    return JSON.stringify(detail.metaData, null, 2);
  }, [detail]);

  const generationTimeText = detail
    ? formatGenerationTimeMs(detail.generationTimeMs)
    : null;
  const generationModeLabel = detail ? getGenerationModeLabel(detail) : null;

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={920}
      centered
      title={
        <Space>
          <PictureOutlined />
          <span>{title}</span>
          {generationModeLabel && <Tag color="gold">{generationModeLabel}</Tag>}
          {detail?.model && <Tag color="blue">{detail.model}</Tag>}
        </Space>
      }
    >
      {detail && (
        <div>
          <div style={{ textAlign: "center", marginBottom: 16 }}>
            <img
              src={detail.imageUrl}
              alt="生成图片"
              style={{
                maxWidth: "100%",
                maxHeight: 520,
                objectFit: "contain",
                borderRadius: 8,
                backgroundColor: "#f5f5f5",
              }}
            />
          </div>
          <Card size="small" style={{ marginTop: 16 }}>
            <Title level={5} style={{ marginBottom: 12 }}>
              生成提示词
            </Title>
            <Paragraph
              style={{
                backgroundColor: "#f5f5f5",
                padding: 12,
                borderRadius: 8,
                marginBottom: 12,
              }}
            >
              {detail.generationPrompt || "暂无生成提示词"}
            </Paragraph>
            <Title level={5} style={{ marginBottom: 12, marginTop: 16 }}>
              生图原始请求
            </Title>
            <Paragraph
              style={{
                backgroundColor: "#f5f5f5",
                padding: 12,
                borderRadius: 8,
                marginBottom: 12,
              }}
            >
              {detail.originalRequest || "暂无原始请求记录"}
            </Paragraph>
            {detail.referenceImages.length > 0 && (
              <>
                <Title level={5} style={{ marginBottom: 12, marginTop: 16 }}>
                  参考图（metadata）
                </Title>
                <div
                  style={{
                    marginBottom: 12,
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fill, minmax(180px, 1fr))",
                    gap: 12,
                  }}
                >
                  {detail.referenceImages.map((referenceImage) => (
                    <div key={`${referenceImage.label}-${referenceImage.url}`}>
                      <div style={{ marginBottom: 6 }}>
                        <Tag>{referenceImage.label}</Tag>
                      </div>
                      <Image
                        src={referenceImage.url}
                        alt={referenceImage.label}
                        style={{
                          width: "100%",
                          maxHeight: 200,
                          objectFit: "contain",
                          borderRadius: 8,
                          backgroundColor: "#f5f5f5",
                        }}
                      />
                    </div>
                  ))}
                </div>
              </>
            )}
            <Space
              size={[8, 4]}
              wrap
              split={<span style={{ color: "#d9d9d9" }}>|</span>}
            >
              {generationModeLabel && (
                <Text type="secondary">生图方式: {generationModeLabel}</Text>
              )}
              <Text type="secondary">
                模型:{" "}
                {detail.model ||
                  (detail.isMatchedFallback
                    ? "兜底匹配（无主模型）"
                    : "未知模型")}
              </Text>
              {detail.userReferenceImageUrl && (
                <Text type="secondary">包含用户参考图: 是</Text>
              )}
              {detail.width && detail.height && (
                <Text type="secondary">
                  尺寸: {detail.width} x {detail.height}
                </Text>
              )}
              <Text type="secondary">
                生成时间: {formatDateTime(detail.createdAt)}
              </Text>
              {generationTimeText && (
                <Text type="secondary">耗时: {generationTimeText}</Text>
              )}
              {detail.modelFallbackDueTo429 !== null && (
                <Text type="secondary">
                  429 备用模型: {detail.modelFallbackDueTo429 ? "是" : "否"}
                </Text>
              )}
              {detail.userId && (
                <Text type="secondary">用户ID: {detail.userId}</Text>
              )}
              {detail.sessionId && (
                <Text type="secondary">会话ID: {detail.sessionId}</Text>
              )}
              {detail.langsmithTraceId && (
                <Text type="secondary">
                  Trace ID: {detail.langsmithTraceId}
                </Text>
              )}
              {detail.langsmithTraceUrl && (
                <a
                  href={detail.langsmithTraceUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  LangSmith Trace
                </a>
              )}
            </Space>
          </Card>

          <Card size="small" style={{ marginTop: 12 }}>
            <Title level={5} style={{ marginBottom: 12 }}>
              图片反馈
            </Title>
            {feedbackLoading ? (
              <Spin size="small" />
            ) : feedbackItems.length === 0 ? (
              <Text type="secondary">暂无图片反馈</Text>
            ) : (
              <List
                size="small"
                dataSource={feedbackItems}
                renderItem={(item) => {
                  const vote = parseFeedbackVote(item.description);
                  const voteTagColor =
                    vote === "like"
                      ? "green"
                      : vote === "dislike"
                        ? "red"
                        : "blue";
                  const voteTagText =
                    vote === "like"
                      ? "点赞反馈"
                      : vote === "dislike"
                        ? "点踩反馈"
                        : "反馈";
                  return (
                    <List.Item key={item.id}>
                      <Space
                        direction="vertical"
                        size={2}
                        style={{ width: "100%" }}
                      >
                        <Space>
                          <Tag color={voteTagColor}>{voteTagText}</Tag>
                          <Text type="secondary">
                            {formatDateTime(item.created_at)}
                          </Text>
                        </Space>
                        <Text>{parseFeedbackContent(item.description)}</Text>
                      </Space>
                    </List.Item>
                  );
                }}
              />
            )}
          </Card>

          <Card size="small" style={{ marginTop: 12 }}>
            <Title level={5} style={{ marginBottom: 12 }}>
              完整 metadata
            </Title>
            <pre
              style={{
                margin: 0,
                backgroundColor: "#f5f5f5",
                padding: 12,
                borderRadius: 8,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                maxHeight: 260,
                overflow: "auto",
                fontSize: 12,
                lineHeight: 1.4,
              }}
            >
              {metadataJson}
            </pre>
          </Card>
        </div>
      )}
    </Modal>
  );
};

export default GeneratedImageDetailModal;
