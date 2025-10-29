/**
 * MessageToImageIcon component for generating images from message content
 * 使用新的聊天生图接口，基于消息ID生成与角色一致的图片
 */

import React, { useState } from "react";
import { Button, Tooltip, Modal, Image, Spin, message } from "antd";
import { PictureOutlined, LoadingOutlined } from "@ant-design/icons";
import { chatImageApi } from "../services/api";

interface MessageToImageIconProps {
  messageId: number; // 消息ID（必填）
  agentId: string; // Agent ID（必填）
  disabled?: boolean;
  size?: "small" | "middle" | "large";
  onImageGenerated?: (imageUrl: string) => void;
}

export const MessageToImageIcon: React.FC<MessageToImageIconProps> = ({
  messageId,
  agentId,
  disabled = false,
  size = "middle",
  onImageGenerated,
}) => {
  const [loading, setLoading] = useState(false);
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);
  const [modalVisible, setModalVisible] = useState(false);

  const handleGenerateImage = async () => {
    setLoading(true);
    try {
      // 创建带超时的 Promise
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => {
          reject(new Error("图片生成超时，请稍后重试"));
        }, 30000); // 30秒超时
      });

      const apiPromise = chatImageApi.generateImage(agentId, {
        message_id: messageId,
        history_count: 10, // 使用最近10条消息作为上下文
      });

      // 使用 Promise.race 来实现超时控制
      const response = await Promise.race([
        apiPromise,
        timeoutPromise,
      ]) as {
        image_url: string;
        image_metadata: {
          width: number;
          height: number;
          format: string;
        };
        prompt: string;
        message_id: number;
      };

      if (response && response.image_url) {
        const imageUrl = response.image_url;
        if (onImageGenerated) {
          // 如果提供了回调函数，调用它来在聊天窗口中显示图片
          onImageGenerated(imageUrl);
          message.success("图片生成成功！");
        } else {
          // 否则使用模态框显示（向后兼容）
          setGeneratedImage(imageUrl);
          setModalVisible(true);
          message.success("图片生成成功！");
        }
      } else {
        message.error("图片生成失败：未返回有效图片");
      }
    } catch (error: any) {
      console.error("Image generation error:", error);
      
      // 处理特定错误
      if (error?.response?.status === 400) {
        message.error("只能对最后一条AI回复生成图片");
      } else {
        const errorMessage =
          error instanceof Error ? error.message : "图片生成失败，请稍后重试";
        message.error(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleModalClose = () => {
    setModalVisible(false);
    setGeneratedImage(null);
  };

  const buttonSize =
    size === "small" ? "small" : size === "large" ? "large" : "middle";

  return (
    <>
      <Tooltip title="根据消息生成与角色一致的图片">
        <Button
          type="text"
          icon={loading ? <LoadingOutlined /> : <PictureOutlined />}
          onClick={handleGenerateImage}
          disabled={disabled || loading}
          size={buttonSize}
          loading={loading}
          style={{
            color: "#666",
            padding: "2px 4px",
            height: "auto",
            minWidth: "auto",
          }}
        />
      </Tooltip>

      <Modal
        title="生成的图片"
        open={modalVisible}
        onCancel={handleModalClose}
        footer={null}
        width={600}
        centered
      >
        <div style={{ textAlign: "center" }}>
          {generatedImage ? (
            <Image
              src={generatedImage}
              alt="Generated image"
              style={{ maxWidth: "100%", maxHeight: "400px" }}
              placeholder={
                <div style={{ textAlign: "center", padding: "50px" }}>
                  <Spin size="large" />
                </div>
              }
            />
          ) : (
            <div style={{ padding: "50px" }}>
              <Spin size="large" />
              <div style={{ marginTop: 16 }}>正在生成图片...</div>
            </div>
          )}
        </div>
      </Modal>
    </>
  );
};
