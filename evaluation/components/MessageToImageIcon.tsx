/**
 * MessageToImageIcon component for generating images from message content
 */

import React, { useState } from "react";
import { Button, Tooltip, Modal, Image, Spin, message } from "antd";
import { PictureOutlined, LoadingOutlined } from "@ant-design/icons";
import { imageApi } from "../services/api";

interface MessageToImageIconProps {
  messageContent: string;
  disabled?: boolean;
  size?: "small" | "middle" | "large";
}

export const MessageToImageIcon: React.FC<MessageToImageIconProps> = ({
  messageContent,
  disabled = false,
  size = "middle",
}) => {
  const [loading, setLoading] = useState(false);
  const [generatedImages, setGeneratedImages] = useState<string[]>([]);
  const [modalVisible, setModalVisible] = useState(false);

  const handleGenerateImage = async () => {
    if (!messageContent.trim()) {
      message.warning("消息内容为空，无法生成图片");
      return;
    }

    setLoading(true);
    try {
      const response = await imageApi.textToImage({
        prompt: messageContent,
        enhance_prompt: false, // Don't enhance for message content
        count: 1, // Generate only 1 image
      });

      if (response.success && response.data) {
        setGeneratedImages(response.data.urls);
        setModalVisible(true);
        message.success("图片生成成功！");
      } else {
        message.error(response.message || "图片生成失败");
      }
    } catch (error) {
      console.error("Image generation error:", error);
      message.error("图片生成失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const handleModalClose = () => {
    setModalVisible(false);
    setGeneratedImages([]);
  };

  const buttonSize = size === "small" ? "small" : size === "large" ? "large" : "middle";

  return (
    <>
      <Tooltip title="根据消息内容生成图片">
        <Button
          type="text"
          icon={loading ? <LoadingOutlined /> : <PictureOutlined />}
          onClick={handleGenerateImage}
          disabled={disabled || loading}
          size={buttonSize}
          loading={loading}
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
          {generatedImages.length > 0 ? (
            <div>
              {generatedImages.map((url, index) => (
                <div key={index} style={{ marginBottom: 16 }}>
                  <Image
                    src={url}
                    alt={`Generated image ${index + 1}`}
                    style={{ maxWidth: "100%", maxHeight: "400px" }}
                    placeholder={
                      <div style={{ textAlign: "center", padding: "50px" }}>
                        <Spin size="large" />
                      </div>
                    }
                  />
                </div>
              ))}
            </div>
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
