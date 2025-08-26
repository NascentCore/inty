import React from "react";
import { Modal, Button, message } from "antd";
import { CopyOutlined } from "@ant-design/icons";

interface JsonDisplayModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  jsonData: string;
  width?: number;
}

export const JsonDisplayModal: React.FC<JsonDisplayModalProps> = ({
  open,
  onClose,
  title = "JSON数据",
  jsonData,
  width = 800,
}) => {
  const handleCopy = () => {
    navigator.clipboard.writeText(jsonData);
    message.success("JSON数据已复制到剪贴板");
  };

  return (
    <Modal
      title={title}
      open={open}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        <Button
          key="copy"
          type="primary"
          icon={<CopyOutlined />}
          onClick={handleCopy}
        >
          复制到剪贴板
        </Button>,
      ]}
      width={width}
      style={{ top: 20 }}
    >
      <div
        style={{
          maxHeight: "60vh",
          overflow: "auto",
          backgroundColor: "#f5f5f5",
          padding: "12px",
          borderRadius: "6px",
          fontFamily: "monospace",
          fontSize: "12px",
          whiteSpace: "pre-wrap",
          wordBreak: "break-all",
        }}
      >
        {jsonData}
      </div>
    </Modal>
  );
};

export default JsonDisplayModal;
