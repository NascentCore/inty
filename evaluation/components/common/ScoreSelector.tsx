import React from "react";
import { Rate, InputNumber, Space, Typography } from "antd";
import { StarOutlined } from "@ant-design/icons";

const { Text } = Typography;

interface ScoreSelectorProps {
  value?: number;
  onChange?: (value?: number) => void;
  disabled?: boolean;
  placeholder?: string;
  showText?: boolean;
  mode?: "star" | "number"; // 星级模式或数字模式
}

const ScoreSelector: React.FC<ScoreSelectorProps> = ({
  value,
  onChange,
  disabled = false,
  placeholder = "选择评分（1-5分）",
  showText = true,
  mode = "star",
}) => {
  const handleChange = (newValue: number | null) => {
    // 确保值在 1-5 范围内，null 表示清空
    if (newValue === null || newValue === 0) {
      onChange?.(undefined);
    } else if (newValue >= 1 && newValue <= 5) {
      onChange?.(newValue);
    }
  };

  const getScoreText = (score?: number) => {
    if (!score) return "未评分";

    const scoreTexts = {
      1: "很差",
      2: "较差",
      3: "一般",
      4: "良好",
      5: "优秀",
    };

    return `${score}分 - ${scoreTexts[score as keyof typeof scoreTexts]}`;
  };

  if (mode === "star") {
    return (
      <Space direction="vertical" size="small">
        <Rate
          value={value || 0}
          onChange={handleChange}
          disabled={disabled}
          character={<StarOutlined />}
          allowClear
          allowHalf={false}
          count={5}
          style={{ fontSize: "18px" }}
        />
        {showText && (
          <Text type="secondary" style={{ fontSize: "12px" }}>
            {value ? getScoreText(value) : placeholder}
          </Text>
        )}
      </Space>
    );
  }

  // 数字模式
  return (
    <Space direction="vertical" size="small">
      <InputNumber
        value={value}
        onChange={handleChange}
        disabled={disabled}
        placeholder={placeholder}
        min={1}
        max={5}
        step={1}
        style={{ width: "100%" }}
        formatter={(val) => (val ? `${val} 分` : "")}
        parser={(val) => (val ? parseInt(val.replace(" 分", ""), 10) : 0)}
      />
      {showText && value && (
        <Text type="secondary" style={{ fontSize: "12px" }}>
          {getScoreText(value)}
        </Text>
      )}
    </Space>
  );
};

export default ScoreSelector;
