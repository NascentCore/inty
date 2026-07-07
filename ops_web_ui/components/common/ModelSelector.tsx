import React from "react";
import { Form, Select, Button } from "antd";
import { SyncOutlined } from "@ant-design/icons";
import type { OpenRouterModel } from "../../types";

const { Option } = Select;

interface ModelSelectorProps {
  name?: string;
  label?: string;
  rules?: Array<{
    required?: boolean;
    message?: string;
    [key: string]: unknown;
  }>;
  value?: string;
  onChange?: (value: string) => void;
  models: OpenRouterModel[];
  loading?: boolean;
  onRefresh?: () => void;
  placeholder?: string;
  style?: React.CSSProperties;
  disabled?: boolean;
  initialValue?: string;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  name = "model",
  label = "模型名称",
  rules = [{ required: true, message: "请选择模型名称" }],
  value,
  onChange,
  models,
  loading = false,
  onRefresh,
  placeholder = "请选择模型",
  style,
  disabled = false,
  initialValue,
}) => {
  // 获取表单实例
  const form = Form.useFormInstance();

  return (
    <Form.Item
      name={name}
      label={label}
      rules={rules}
      style={style}
      initialValue={initialValue}
    >
      <div style={{ display: "flex", gap: 8 }}>
        <Select
          style={{ flex: 1 }}
          placeholder={placeholder}
          showSearch
          value={value}
          onChange={(val) => {
            // 确保表单字段值被正确更新
            if (onChange) {
              onChange(val);
            }
            // 如果是在Form内部使用，还需要手动更新表单字段
            if (!onChange && name && form) {
              form.setFieldValue(name, val);
            }
          }}
          filterOption={(input, option) =>
            String(option?.label ?? "")
              .toLowerCase()
              .includes(input.toLowerCase()) ||
            String(option?.value ?? "")
              .toLowerCase()
              .includes(input.toLowerCase())
          }
          loading={loading}
          notFoundContent={loading ? "加载中..." : "暂无数据"}
          disabled={disabled}
        >
          {models.map((model) => (
            <Option key={model.id} value={model.id} label={model.name}>
              <div>
                <div style={{ fontWeight: 500 }}>{model.name}</div>
                {model.description && (
                  <div style={{ fontSize: "12px", color: "#666" }}>
                    {model.description}
                  </div>
                )}
              </div>
            </Option>
          ))}
        </Select>
        {onRefresh && (
          <Button
            icon={<SyncOutlined />}
            onClick={onRefresh}
            loading={loading}
            title="刷新模型列表"
            disabled={disabled}
          />
        )}
      </div>
    </Form.Item>
  );
};

export default ModelSelector;
