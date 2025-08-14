import React from "react";
import { Typography, Button, Input, Tooltip } from "antd";
import { PlusOutlined, MinusCircleOutlined } from "@ant-design/icons";
import { VariableSet } from "../../pages/PromptEvaluationPage";

const { Title, Text } = Typography;

interface VariableEditorProps {
  variableSets: VariableSet[];
  onUpdateVariable: (setId: string, key: string, value: string) => void;
  onDeleteVariable: (setId: string, key: string) => void;
  onAddVariable: (setId: string) => void;
}

export const VariableEditor: React.FC<VariableEditorProps> = ({
  variableSets,
  onUpdateVariable,
  onDeleteVariable,
  onAddVariable,
}) => {
  return (
    <div>
      <div style={{ marginBottom: "16px" }}>
        <Title level={4} style={{ margin: 0, color: "#1890ff" }}>
          输入变量
        </Title>
        <Text type="secondary">
          定义一个或多个变量，用于填充提示词模版中的变量
        </Text>
      </div>

      {/* 变量列表 */}
      {Object.entries(variableSets[0]?.variables || {}).map(([key, value]) => (
        <div
          key={key}
          style={{
            display: "flex",
            alignItems: "center",
            marginBottom: "12px",
            gap: "8px",
          }}
        >
          <Input
            placeholder="变量名"
            value={key}
            onChange={(e) => {
              const newKey = e.target.value;
              if (newKey !== key) {
                // 创建新的变量对象，替换旧的键
                const newVariables = { ...variableSets[0].variables };
                delete newVariables[key];
                newVariables[newKey] = value;
                onUpdateVariable(variableSets[0].id, newKey, value);
              }
            }}
            style={{ flex: 1 }}
            size="small"
          />
          <Input
            placeholder="变量值"
            value={value}
            onChange={(e) =>
              onUpdateVariable(variableSets[0].id, key, e.target.value)
            }
            style={{ flex: 2 }}
            size="small"
          />
          <Tooltip title="删除变量">
            <Button
              type="text"
              icon={<MinusCircleOutlined />}
              onClick={() => onDeleteVariable(variableSets[0].id, key)}
              size="small"
              danger
            />
          </Tooltip>
        </div>
      ))}

      {/* 添加变量按钮 */}
      <Button
        type="dashed"
        icon={<PlusOutlined />}
        onClick={() => onAddVariable(variableSets[0]?.id || "1")}
        size="small"
        style={{ width: "100%" }}
      >
        添加变量
      </Button>
    </div>
  );
};
