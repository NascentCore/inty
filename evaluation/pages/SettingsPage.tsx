import React, { useEffect, useState } from "react";
import {
  Card,
  Form,
  Input,
  InputNumber,
  Button,
  message,
  Spin,
  Typography,
  Select,
  Divider,
} from "antd";
import { SaveOutlined, ReloadOutlined } from "@ant-design/icons";
import { chatImageApi } from "../services/api";

// 消息生图模型：仅允许 models_catalog 中的四个 nickname
const CHAT_IMAGE_MODEL_OPTIONS = [
  {
    value: "Nano Banana",
    label: "Nano Banana",
    description: "Gemini 2.5 Flash Image",
  },
  {
    value: "Nano Banana Pro",
    label: "Nano Banana Pro",
    description: "Gemini 3 Pro Image Preview",
  },
  {
    value: "Seedream V4.5 Edit",
    label: "Seedream V4.5 Edit",
    description: "fal.ai Seedream 编辑",
  },
  {
    value: "Z Image Turbo Image to Image",
    label: "Z Image Turbo Image to Image",
    description: "fal.ai Z-Image image-to-image",
  },
];

const { Title, Text } = Typography;
const { TextArea } = Input;

/**
 * 设置页面
 * 用于管理图片生成配置等系统设置
 */
export const SettingsPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const getErrorMessage = (error: unknown, fallback: string) => {
    if (error instanceof Error && error.message) {
      return error.message;
    }
    if (
      typeof error === "object" &&
      error !== null &&
      "message" in error &&
      typeof (error as { message?: unknown }).message === "string"
    ) {
      return (error as { message: string }).message;
    }
    return fallback;
  };

  // 加载配置
  const loadConfig = async () => {
    try {
      setLoading(true);
      const response = await chatImageApi.getConfig();
      if (response) {
        form.setFieldsValue({
          prompt_template: response.prompt_template,
          default_history_count: response.default_history_count,
          free_user_chat_image_model: response.free_user_chat_image_model,
          sub_user_chat_image_model: response.sub_user_chat_image_model,
        });
        message.success("配置加载成功");
      }
    } catch (error: unknown) {
      message.error(`加载配置失败: ${getErrorMessage(error, "未知错误")}`);
      console.error("加载配置失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 保存配置
  const saveConfig = async () => {
    try {
      setSaving(true);
      const values = await form.validateFields();
      const response = await chatImageApi.updateConfig(values);
      if (response) {
        message.success("配置保存成功");
        form.setFieldsValue({
          prompt_template: response.prompt_template,
          default_history_count: response.default_history_count,
          free_user_chat_image_model: response.free_user_chat_image_model,
          sub_user_chat_image_model: response.sub_user_chat_image_model,
        });
      }
    } catch (error: unknown) {
      if (
        typeof error === "object" &&
        error !== null &&
        "errorFields" in error
      ) {
        message.error("请检查表单填写");
      } else {
        message.error(`保存配置失败: ${getErrorMessage(error, "未知错误")}`);
        console.error("保存配置失败:", error);
      }
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    loadConfig();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <Title level={2}>系统设置</Title>

      <Spin spinning={loading}>
        <Card
          title="图片生成配置"
          extra={
            <Button
              icon={<ReloadOutlined />}
              onClick={loadConfig}
              disabled={loading}
            >
              重新加载
            </Button>
          }
          style={{ marginBottom: 24 }}
        >
          <Form form={form} layout="vertical">
            <Form.Item
              name="prompt_template"
              label="提示词模板"
              rules={[{ required: true, message: "请输入提示词模板" }]}
              extra={
                <Text type="secondary">
                  支持变量：{"{agent_background}"}, {"{agent_personality}"},{" "}
                  {"{chat_history}"}, {"{user_message}"}, {"{user_info}"}
                </Text>
              }
            >
              <TextArea
                rows={10}
                placeholder="输入提示词模板..."
                style={{ fontFamily: "monospace" }}
              />
            </Form.Item>

            <Form.Item
              name="default_history_count"
              label="默认历史消息数量"
              rules={[
                { required: true, message: "请输入默认历史消息数量" },
                {
                  type: "number",
                  min: 1,
                  max: 50,
                  message: "请输入1-50之间的数字",
                },
              ]}
              extra={
                <Text type="secondary">
                  生成图片时默认使用的聊天历史消息数量
                </Text>
              }
            >
              <InputNumber
                min={1}
                max={50}
                style={{ width: "100%" }}
                placeholder="例如：10"
              />
            </Form.Item>

            <Divider orientation="left">消息生图模型配置</Divider>
            <Text
              type="secondary"
              style={{ display: "block", marginBottom: 16 }}
            >
              使用 models_catalog 中的模型 nickname（仅允许：Nano Banana、Nano
              Banana Pro、Seedream V4.5 Edit、Z Image Turbo Image to Image）
            </Text>

            <Form.Item
              name="free_user_chat_image_model"
              label="免费用户 - 模型"
              rules={[{ required: true, message: "请选择模型" }]}
            >
              <Select
                placeholder="选择免费用户模型"
                options={CHAT_IMAGE_MODEL_OPTIONS.map((opt) => ({
                  value: opt.value,
                  label: (
                    <span>
                      {opt.label}{" "}
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        - {opt.description}
                      </Text>
                    </span>
                  ),
                }))}
              />
            </Form.Item>

            <Form.Item
              name="sub_user_chat_image_model"
              label="订阅用户 - 模型"
              rules={[{ required: true, message: "请选择模型" }]}
            >
              <Select
                placeholder="选择订阅用户模型"
                options={CHAT_IMAGE_MODEL_OPTIONS.map((opt) => ({
                  value: opt.value,
                  label: (
                    <span>
                      {opt.label}{" "}
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        - {opt.description}
                      </Text>
                    </span>
                  ),
                }))}
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={saveConfig}
                loading={saving}
                size="large"
              >
                保存配置
              </Button>
              <Text type="secondary" style={{ marginLeft: 16 }}>
                注意：配置保存后仅在内存中生效，重启后恢复到 config.yaml 中的值
              </Text>
            </Form.Item>
          </Form>
        </Card>
      </Spin>
    </div>
  );
};

export default SettingsPage;
