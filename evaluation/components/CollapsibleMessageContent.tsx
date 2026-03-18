import React from "react";
import { Typography } from "antd";

const { Text, Paragraph } = Typography;

interface CollapsibleMessageContentProps {
  content: string | null | undefined;
}

export const CollapsibleMessageContent: React.FC<
  CollapsibleMessageContentProps
> = ({ content }) => {
  const normalizedContent = typeof content === "string" ? content.trim() : "";
  if (!normalizedContent) {
    return <Text type="secondary">[无文本内容]</Text>;
  }

  return (
    <Paragraph
      style={{
        marginBottom: 0,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}
      ellipsis={{ rows: 2, expandable: true, symbol: "展开" }}
    >
      {normalizedContent}
    </Paragraph>
  );
};
