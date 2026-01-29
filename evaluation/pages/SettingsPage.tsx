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

// 消息生图模型选项：第一级选择提供商（Gemini 或 fal.ai），选 Gemini 时具体型号由下方「Gemini 模型 ID」决定
const CHAT_IMAGE_MODEL_OPTIONS = [
  {
    value: "gemini",
    label: "Gemini（Vertex AI）",
    description: "由下方 Gemini 模型 ID 指定具体型号",
  },
  {
    value: "fal-ai/z-image/turbo/image-to-image",
    label: "fal-ai/z-image/turbo/image-to-image",
    description: "Tongyi-MAI 超快速 6B 参数模型",
  },
  {
    value: "fal-ai/flux/dev/image-to-image",
    label: "FLUX Dev (fal.ai)",
    description: "FLUX 开发版 image-to-image 模型",
  },
  {
    value: "fal-ai/stable-diffusion-v3-medium/image-to-image",
    label: "SD v3 Medium (fal.ai)",
    description: "Stable Diffusion v3 中型模型",
  },
  {
    value: "fal-ai/gpt-image-1.5/edit",
    label: "fal-ai/gpt-image-1.5/edit",
    description: "GPT Image 1.5 编辑模型",
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
          free_user_chat_image_gemini_model: response.free_user_chat_image_gemini_model,
          sub_user_chat_image_gemini_model: response.sub_user_chat_image_gemini_model,
        });
        message.success("配置加载成功");
      }
    } catch (error: any) {
      message.error(`加载配置失败: ${error.message || "未知错误"}`);
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
          free_user_chat_image_gemini_model: response.free_user_chat_image_gemini_model,
          sub_user_chat_image_gemini_model: response.sub_user_chat_image_gemini_model,
        });
      }
    } catch (error: any) {
      if (error.errorFields) {
        message.error("请检查表单填写");
      } else {
        message.error(`保存配置失败: ${error.message || "未知错误"}`);
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
            <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
              先选提供商（Gemini 或 fal.ai），选 Gemini 时由下方「Gemini 模型
              ID」指定具体型号（如 gemini-2.5-flash-image、gemini-3-pro-image-preview）
            </Text>

            <Form.Item
              name="free_user_chat_image_model"
              label="免费用户 - 模型提供商"
              rules={[{ required: true, message: "请选择模型提供商" }]}
              extra={
                <Text type="secondary">
                  选 Gemini 时使用下方「免费用户 Gemini 模型 ID」；选 fal.ai 时直接使用对应模型
                </Text>
              }
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
              label="订阅用户 - 模型提供商"
              rules={[{ required: true, message: "请选择模型提供商" }]}
              extra={
                <Text type="secondary">
                  选 Gemini 时使用下方「订阅用户 Gemini 模型 ID」；推荐 gemini-3-pro-image-preview
                </Text>
              }
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

            <Form.Item
              name="free_user_chat_image_gemini_model"
              label="免费用户 Gemini 模型 ID"
              rules={[{ required: true, message: "请输入 Vertex AI 模型 ID" }]}
              extra={
                <Text type="secondary">
                  仅当上方「免费用户 - 模型提供商」选 Gemini 时生效，如 gemini-2.5-flash-image
                </Text>
              }
            >
              <Input placeholder="例如：gemini-2.5-flash-image" />
            </Form.Item>

            <Form.Item
              name="sub_user_chat_image_gemini_model"
              label="订阅用户 Gemini 模型 ID"
              rules={[{ required: true, message: "请输入 Vertex AI 模型 ID" }]}
              extra={
                <Text type="secondary">
                  仅当上方「订阅用户 - 模型提供商」选 Gemini 时生效，如 gemini-3-pro-image-preview
                </Text>
              }
            >
              <Input placeholder="例如：gemini-3-pro-image-preview" />
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
