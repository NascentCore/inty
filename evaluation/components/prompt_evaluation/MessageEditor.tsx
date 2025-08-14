import React, { useState } from "react";
import { Select, Button, Input, Space, Tooltip } from "antd";
import {
  CopyOutlined,
  DeleteOutlined,
  DragOutlined,
  MoreOutlined,
} from "@ant-design/icons";
import { Message } from "../../pages/PromptEvaluationPage";

const { TextArea } = Input;

interface MessageEditorProps {
  message: Message;
  index: number;
  onUpdate: (updates: Partial<Message>) => void;
  onDelete: () => void;
  onCopy: () => void;
  onReorder: (fromIndex: number, toIndex: number) => void;
  isSelected: boolean;
}

export const MessageEditor: React.FC<MessageEditorProps> = ({
  message,
  index,
  onUpdate,
  onDelete,
  onCopy,
  onReorder,
  isSelected,
}) => {
  const [isDragging, setIsDragging] = useState(false);

  const handleRoleChange = (role: "system" | "assistant" | "user") => {
    onUpdate({ role });
  };

  const handleContentChange = (content: string) => {
    onUpdate({ content });
  };

  const handleDragStart = (e: React.DragEvent) => {
    setIsDragging(true);
    e.dataTransfer.setData("text/plain", index.toString());
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const fromIndex = parseInt(e.dataTransfer.getData("text/plain"));
    const toIndex = index;
    if (fromIndex !== toIndex) {
      onReorder(fromIndex, toIndex);
    }
    setIsDragging(false);
  };

  const handleDragEnd = () => {
    setIsDragging(false);
  };

  return (
    <div
      style={{
        border: isSelected ? "2px solid #1890ff" : "1px solid #d9d9d9",
        borderRadius: "8px",
        marginBottom: "16px",
        background: "#fff",
        transition: "all 0.2s",
        opacity: isDragging ? 0.5 : 1,
        transform: isDragging ? "scale(0.98)" : "scale(1)",
      }}
      draggable
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onDragEnd={handleDragEnd}
    >
      {/* 消息头部 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "12px 16px",
          borderBottom: "1px solid #f0f0f0",
          background: "#fafafa",
          borderTopLeftRadius: "8px",
          borderTopRightRadius: "8px",
        }}
      >
        {/* 拖拽手柄 */}
        <div
          style={{
            cursor: "grab",
            marginRight: "12px",
            color: "#8c8c8c",
            display: "flex",
            alignItems: "center",
          }}
          title="拖拽重新排序"
        >
          <DragOutlined style={{ fontSize: "16px" }} />
        </div>

        {/* 角色选择下拉菜单 */}
        <Select
          value={message.role}
          onChange={handleRoleChange}
          style={{ width: "120px", marginRight: "12px" }}
          options={[
            { label: "System", value: "system" },
            { label: "Assistant", value: "assistant" },
            { label: "User", value: "user" },
          ]}
        />

        {/* 复制按钮 */}
        <Tooltip title="复制消息内容">
          <Button
            type="text"
            icon={<CopyOutlined />}
            onClick={onCopy}
            size="small"
            style={{ marginRight: "8px" }}
          />
        </Tooltip>

        {/* 删除按钮 */}
        <Tooltip title="删除消息">
          <Button
            type="text"
            icon={<DeleteOutlined />}
            onClick={onDelete}
            size="small"
            danger
          />
        </Tooltip>
      </div>

      {/* 消息内容编辑区域 */}
      <div style={{ padding: "16px" }}>
        <TextArea
          value={message.content}
          onChange={(e) => handleContentChange(e.target.value)}
          placeholder={`输入 ${message.role} 消息内容...`}
          autoSize={{ minRows: 3, maxRows: 8 }}
          style={{
            border: "none",
            resize: "none",
            fontSize: "14px",
            lineHeight: "1.6",
          }}
        />
      </div>
    </div>
  );
};
