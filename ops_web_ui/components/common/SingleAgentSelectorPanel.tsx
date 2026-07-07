import React, { useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Empty,
  Input,
  List,
  Space,
  Tag,
  Typography,
} from "antd";
import { ReloadOutlined, RobotOutlined } from "@ant-design/icons";
import { useAgents } from "../../hooks/useAgents";
import type { Agent } from "../../types";
import {
  filterAgentsForSingleSelector,
  shouldShowSingleSelectorEmptySearch,
} from "../../utils/singleAgentSelector";
import { AvatarDisplay } from "./AvatarDisplay";

const { Search } = Input;
const { Text } = Typography;

const getGenderTagConfig = (gender?: Agent["gender"]) => {
  if (!gender) {
    return null;
  }

  if (gender === "MALE") {
    return { color: "blue", label: "男" };
  }

  if (gender === "FEMALE") {
    return { color: "pink", label: "女" };
  }

  return { color: "default", label: "其他" };
};

const getVisibilityTagConfig = (visibility: Agent["visibility"]) => {
  if (visibility === "PUBLIC") {
    return { color: "green", label: "公开" };
  }
  return { color: "orange", label: "私有" };
};

interface SingleAgentSelectorPanelProps {
  selectedAgentId?: string;
  onSelectAgent: (agent: Agent) => void;
}

// 关键步骤总结：
// 1) 将 ChatPage 与 VoiceChatPage 的单选侧栏统一为一个组件，确保视觉和交互一致。
// 2) 保留“刷新/搜索/选中高亮/标签展示/空态与错误态”这一套完整行为，避免页面间出现交互差异。
// 3) 页面仅保留业务差异逻辑（例如语音通话中的“通话中禁止切换角色”校验），侧栏只负责展示与选择。
export const SingleAgentSelectorPanel: React.FC<
  SingleAgentSelectorPanelProps
> = ({ selectedAgentId, onSelectAgent }) => {
  const [searchText, setSearchText] = useState("");
  const {
    agents,
    loading: agentsLoading,
    error: agentsError,
    loadAgents,
  } = useAgents({
    type: "all",
    autoLoad: true,
  });

  const filteredAgents = useMemo(
    () => filterAgentsForSingleSelector(agents, searchText),
    [agents, searchText],
  );
  const showSearchEmpty = shouldShowSingleSelectorEmptySearch(
    agents.length,
    searchText,
    filteredAgents.length,
  );

  return (
    <Card
      title={
        <Space>
          <RobotOutlined />
          选择智能体
        </Space>
      }
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
      styles={{
        body: { flex: 1, padding: "16px", overflow: "hidden" },
      }}
      extra={
        <Button
          icon={<ReloadOutlined />}
          size="small"
          onClick={() => loadAgents(true)}
          loading={agentsLoading}
        />
      }
    >
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Search
          allowClear
          value={searchText}
          placeholder="搜索智能体名称"
          onChange={(event) => setSearchText(event.target.value)}
        />
        <div
          style={{
            marginTop: 12,
            flex: 1,
            overflowY: "auto",
          }}
        >
          {agentsError ? (
            <Alert
              message="加载失败"
              description={agentsError}
              type="error"
              showIcon
            />
          ) : agents.length === 0 ? (
            <Empty
              description="暂无可用智能体"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : showSearchEmpty ? (
            <Empty
              description="未找到匹配的智能体"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <List
              loading={agentsLoading}
              dataSource={filteredAgents}
              renderItem={(agent) => {
                const isSelected = selectedAgentId === agent.id;
                const genderTag = getGenderTagConfig(agent.gender);
                const visibilityTag = getVisibilityTagConfig(agent.visibility);

                return (
                  <List.Item
                    className={`agent-item ${isSelected ? "selected" : ""}`}
                    style={{
                      cursor: "pointer",
                      padding: "12px",
                      border: isSelected
                        ? "2px solid #1890ff"
                        : "1px solid #f0f0f0",
                      borderRadius: "8px",
                      marginBottom: "8px",
                      backgroundColor: isSelected ? "#f6ffed" : "#fff",
                      transition: "all 0.2s ease",
                    }}
                    onClick={() => onSelectAgent(agent)}
                  >
                    <List.Item.Meta
                      avatar={<AvatarDisplay agent={agent} size={40} />}
                      title={
                        <Text strong style={{ fontSize: "14px" }}>
                          {agent.name}
                        </Text>
                      }
                      description={
                        <div>
                          <Text
                            type="secondary"
                            style={{
                              fontSize: "12px",
                              lineHeight: "1.4",
                              whiteSpace: "pre-wrap",
                              wordBreak: "break-word",
                              display: "block",
                            }}
                          >
                            {agent.intro}
                          </Text>
                          <div style={{ marginTop: 4 }}>
                            {genderTag && (
                              <Tag color={genderTag.color}>
                                {genderTag.label}
                              </Tag>
                            )}
                            <Tag color={visibilityTag.color}>
                              {visibilityTag.label}
                            </Tag>
                          </div>
                        </div>
                      }
                    />
                  </List.Item>
                );
              }}
            />
          )}
        </div>
      </div>
    </Card>
  );
};
