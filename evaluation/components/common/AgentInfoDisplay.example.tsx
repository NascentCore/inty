/**
 * AgentInfoDisplay 组件使用示例
 * 展示如何在不同场景下使用 AgentInfoDisplay 组件
 */

import React from "react";
import { Card, Space } from "antd";
import AgentInfoDisplay from "./AgentInfoDisplay";
import type { Agent } from "../../types";

// 示例数据
const exampleAgent: Agent = {
  id: "agent-123",
  name: "示例智能体",
  gender: "FEMALE",
  intro: "这是一个示例智能体的简介",
  opening: "你好！我是示例智能体，很高兴认识你！",
  visibility: "PUBLIC",
  main_prompt: "你是一个友好的AI助手...",
  personality: "性格开朗，喜欢帮助他人...",
  mode_prompt: "在聊天中保持友好和专业...",
  avatar: "https://example.com/avatar.jpg",
  background: "https://example.com/background.jpg",
  background_images: ["https://example.com/bg1.jpg", "https://example.com/bg2.jpg"],
  description: "这是一个详细的描述",
  voice_id: "voice-123",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-02T00:00:00Z",
  llm_config: {
    model: "gpt-4",
    temperature: 0.7,
    max_tokens: 2048,
    top_p: 1.0,
    frequency_penalty: 0,
    presence_penalty: 0,
  },
};

export const AgentInfoDisplayExamples: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      {/* 完整信息展示 */}
      <Card title="完整信息展示">
        <AgentInfoDisplay agent={exampleAgent} />
      </Card>

      {/* 紧凑模式展示 */}
      <Card title="紧凑模式展示">
        <AgentInfoDisplay 
          agent={exampleAgent} 
          compact={true}
        />
      </Card>

      {/* 仅显示基本信息 */}
      <Card title="仅显示基本信息">
        <AgentInfoDisplay 
          agent={exampleAgent}
          showImages={false}
          showPrompts={false}
          showLLMConfig={false}
        />
      </Card>

      {/* 不显示图片资源 */}
      <Card title="不显示图片资源">
        <AgentInfoDisplay 
          agent={exampleAgent}
          showImages={false}
        />
      </Card>

      {/* 不显示提示词配置 */}
      <Card title="不显示提示词配置">
        <AgentInfoDisplay 
          agent={exampleAgent}
          showPrompts={false}
        />
      </Card>

      {/* 不显示LLM配置 */}
      <Card title="不显示LLM配置">
        <AgentInfoDisplay 
          agent={exampleAgent}
          showLLMConfig={false}
        />
      </Card>
    </Space>
  );
};

export default AgentInfoDisplayExamples;
