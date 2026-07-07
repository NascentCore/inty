/**
 * API Key 输入模态框组件
 * 用于用户输入和验证 API Key
 */

import React, { useState } from "react";
import { Modal, Input, Button, Form, Alert, Space } from "antd";
import { KeyOutlined, InfoCircleOutlined } from "@ant-design/icons";
import { useApiKeyContext } from "../hooks/useApiKey";

interface ApiKeyModalProps {
  visible: boolean;
  onClose: () => void;
  allowClose?: boolean; // 是否允许关闭模态框
}

export const ApiKeyModal: React.FC<ApiKeyModalProps> = ({
  visible,
  onClose,
  allowClose = true,
}) => {
  const [form] = Form.useForm();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { setApiKey, isLoading } = useApiKeyContext();

  const handleSubmit = async (values: { apiKey: string }) => {
    setIsSubmitting(true);
    const success = await setApiKey(values.apiKey);
    if (success) {
      form.resetFields();
      onClose();
    }
    setIsSubmitting(false);
  };

  const handleCancel = () => {
    // 只有在允许关闭且不在提交状态时才能关闭
    if (allowClose && !isSubmitting && !isLoading) {
      form.resetFields();
      onClose();
    }
  };

  return (
    <Modal
      open={visible}
      onCancel={
        allowClose && !isSubmitting && !isLoading ? handleCancel : undefined
      }
      footer={null}
      width={500}
      centered
      maskClosable={false}
      closable={allowClose && !isSubmitting && !isLoading}
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
            {allowClose && (
              <Button
                onClick={handleCancel}
                disabled={isSubmitting || isLoading}
              >
                取消
              </Button>
            )}
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
    </Modal>
  );
};
