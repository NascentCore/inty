import React from "react";
import { Typography, Button, Space, Empty, Tooltip } from "antd";
import { PlayCircleOutlined, PlusOutlined } from "@ant-design/icons";

const { Title, Text, Paragraph } = Typography;

interface OutputDisplayProps {
  outputs: string[];
  onAddToNextRound: (output: string) => void;
}

export const OutputDisplay: React.FC<OutputDisplayProps> = ({
  outputs,
  onAddToNextRound,
}) => {
  if (outputs.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "40px 20px" }}>
        <PlayCircleOutlined
          style={{ fontSize: "48px", color: "#d9d9d9", marginBottom: "16px" }}
        />
        <Title level={4} style={{ color: "#8c8c8c", marginBottom: "8px" }}>
          执行提示词查看输出
        </Title>
        <Text type="secondary">点击执行按钮运行提示词，结果将显示在这里</Text>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: "16px" }}>
        <Title level={4} style={{ margin: 0, color: "#1890ff" }}>
          输出结果
        </Title>
        <Text type="secondary">查看AI模型的响应结果</Text>
      </div>

      {outputs.map((output, index) => (
        <div
          key={index}
          style={{
            background: "#f8f9fa",
            border: "1px solid #e9ecef",
            borderRadius: "6px",
            padding: "16px",
            marginBottom: "16px",
          }}
        >
          <div style={{ marginBottom: "12px" }}>
            <Text strong style={{ color: "#1890ff" }}>
              输出 {index + 1}
            </Text>
          </div>

          <Paragraph
            style={{
              margin: 0,
              fontSize: "14px",
              lineHeight: "1.6",
              color: "#262626",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {output}
          </Paragraph>

          <div style={{ marginTop: "12px" }}>
            <Tooltip title="将此响应添加到下一轮对话">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => onAddToNextRound(output)}
                size="small"
              >
                添加到下一轮
              </Button>
            </Tooltip>
          </div>
        </div>
      ))}
    </div>
  );
};
