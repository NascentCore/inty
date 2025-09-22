/**
 * API Key 输入模态框组件
 * 用于用户输入和验证 API Key
 */

import React, { useState } from "react";
import { Modal, Input, Button, Form, Typography, Alert, Space } from "antd";
import { KeyOutlined, InfoCircleOutlined } from "@ant-design/icons";
import { useApiKeyContext } from "../hooks/useApiKey";

const { Text } = Typography;

interface ApiKeyModalProps {
  visible: boolean;
  onClose: () => void;
}

export const ApiKeyModal: React.FC<ApiKeyModalProps> = ({ visible, onClose }) => {
  const [form] = Form.useForm();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { setApiKey, isLoading } = useApiKeyContext();

  const handleSubmit = async (values: { apiKey: string }) => {
    setIsSubmitting(true);
    await setApiKey(values.apiKey);
    form.resetFields();
    onClose();
    setIsSubmitting(false);
  };

  const handleCancel = () => {
    form.resetFields();
    onClose();
  };

  return (
    <Modal
      title={
        <Space>
          <KeyOutlined style={{ color: "#1890ff" }} />
          <span>设置 API Key</span>
        </Space>
      }
      open={visible}
      onCancel={handleCancel}
      footer={null}
      width={500}
      centered
      maskClosable={false}
      closable={!isSubmitting}
    >
      <div style={{ marginBottom: 16 }}>
        <Alert
          message="需要 API Key 才能使用评测系统"
          description="请输入您的 InTy API Key 以访问智能体评测功能。如果您没有 API Key，请联系管理员获取。"
          type="info"
          icon={<InfoCircleOutlined />}
          showIcon
        />
      </div>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        disabled={isSubmitting || isLoading}
      >
        <Form.Item
          name="apiKey"
          label="API Key"
          rules={[
            { required: true, message: "请输入 API Key" },
            { min: 10, message: "API Key 长度至少为 10 个字符" },
          ]}
        >
          <Input.Password
            placeholder="请输入您的 API Key"
            size="large"
            prefix={<KeyOutlined style={{ color: "#bfbfbf" }} />}
            autoComplete="off"
            autoFocus
          />
        </Form.Item>

        <Form.Item style={{ marginBottom: 0, textAlign: "right" }}>
          <Space>
            <Button onClick={handleCancel} disabled={isSubmitting || isLoading}>
              取消
            </Button>
            <Button
              type="primary"
              htmlType="submit"
              loading={isSubmitting || isLoading}
              size="large"
            >
              {isSubmitting || isLoading ? "验证中..." : "确认"}
            </Button>
          </Space>
        </Form.Item>
      </Form>

      <div style={{ marginTop: 16, padding: 12, backgroundColor: "#f5f5f5", borderRadius: 6 }}>
        <Text type="secondary" style={{ fontSize: "12px" }}>
          <InfoCircleOutlined style={{ marginRight: 4 }} />
          API Key 将安全存储在浏览器中，不会发送到第三方服务器。
        </Text>
      </div>
    </Modal>
  );
};
