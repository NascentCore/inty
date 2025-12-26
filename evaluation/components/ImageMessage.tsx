import React from "react";
import { Card, Image, Tag, Typography } from "antd";
import { PictureOutlined } from "@ant-design/icons";
import { formatUtcTime } from "../utils/dateUtils";

const { Text, Paragraph } = Typography;

interface ImageMessageProps {
  imageUrl: string;
  imageMetadata?: {
    width: number;
    height: number;
    format: string;
  };
  prompt?: string;
  timestamp?: string;
  className?: string;
}

/**
 * 图片消息组件
 * 用于在聊天界面中显示AI生成的图片消息
 */
export const ImageMessage: React.FC<ImageMessageProps> = ({
  imageUrl,
  imageMetadata,
  prompt,
  timestamp,
  className,
}) => {
  return (
    <Card
      className={className}
      style={{ maxWidth: 600, marginBottom: 16 }}
      cover={
        <Image
          src={imageUrl}
          alt="AI生成的图片"
          placeholder={
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                height: 200,
                background: "#f0f0f0",
              }}
            >
              <PictureOutlined style={{ fontSize: 48, color: "#bfbfbf" }} />
            </div>
          }
        />
      }
    >
      {imageMetadata && (
        <div style={{ marginBottom: 8 }}>
          <Tag color="blue">
            {imageMetadata.width} x {imageMetadata.height}
          </Tag>
          <Tag color="green">{imageMetadata.format.toUpperCase()}</Tag>
        </div>
      )}
      {timestamp && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {formatUtcTime(timestamp)}
        </Text>
      )}
      {prompt && (
        <Paragraph
          ellipsis={{ rows: 2, expandable: true, symbol: "展开" }}
          style={{ marginTop: 8, marginBottom: 0 }}
        >
          <Text type="secondary" style={{ fontSize: 12 }}>
            提示词: {prompt}
          </Text>
        </Paragraph>
      )}
    </Card>
  );
};

export default ImageMessage;
