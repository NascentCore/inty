/**
 * 生成图片详情弹窗（支持完整 metadata 展示）
 * CREATED_BY_AGENT
 */
import React, { useMemo } from "react";
import { Card, Image, Modal, Space, Tag, Typography } from "antd";
import { PictureOutlined } from "@ant-design/icons";
import { formatUtcTimeRaw } from "../../utils/dateUtils";
import type { GeneratedImageDetail } from "../../utils/generatedImageDetail";

const { Text, Paragraph, Title } = Typography;

interface GeneratedImageDetailModalProps {
  open: boolean;
  onClose: () => void;
  detail: GeneratedImageDetail | null;
  title?: string;
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

export const GeneratedImageDetailModal: React.FC<
  GeneratedImageDetailModalProps
> = ({ open, onClose, detail, title = "图片详情" }) => {
  const metadataJson = useMemo(() => {
    if (!detail || Object.keys(detail.metaData).length === 0) {
      return "暂无 metadata";
    }
    return JSON.stringify(detail.metaData, null, 2);
  }, [detail]);

  const generationTimeText = detail
    ? formatGenerationTimeMs(detail.generationTimeMs)
    : null;

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
              <Text type="secondary">模型: {detail.model || "未知模型"}</Text>
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
            </Space>
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
