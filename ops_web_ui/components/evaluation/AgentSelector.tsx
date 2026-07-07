/**
 * 智能体选择器组件
 * 负责智能体的选择、管理、创建功能
 */

import React, { useState, useCallback, useMemo } from "react";
import {
  Card,
  List,
  Button,
  Space,
  Tag,
  Input,
  Select,
  Checkbox,
  Tooltip,
  Empty,
  Badge,
  Row,
  Col,
  message,
} from "antd";
import {
  RobotOutlined,
  CheckCircleOutlined,
  GlobalOutlined,
  LockOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useAgents } from "../../hooks/useAgents";
import { AvatarDisplay } from "../common/AvatarDisplay";
import { formatUtcTimeRaw } from "../../utils/dateUtils";

const { Search } = Input;
const { Option } = Select;

interface AgentSelectorProps {
  selectedAgents: string[];
  onChange: (selectedAgents: string[]) => void;
  maxSelection?: number;
}

export const AgentSelector: React.FC<AgentSelectorProps> = ({
  selectedAgents,
  onChange,
  maxSelection = 10,
}) => {
  // 状态管理
  const [searchText, setSearchText] = useState("");
  const [visibilityFilter, setVisibilityFilter] = useState<string>("all");

  // 智能体数据 - 使用现有的agents API
  const { agents, loading, error, loadAgents } = useAgents({
    type: "all", // 获取所有智能体，然后前端过滤
    autoLoad: true,
    enableCache: true,
    useRecommended: false, // 不使用推荐API，使用完整列表
  });

  // 过滤智能体
  const filteredAgents = useMemo(() => {
    // 确保agents是数组，处理可能的API响应格式问题
    let agentsArray = agents;

    // 如果agents是{code, message, data}格式，提取data
    if (
      agents &&
      typeof agents === "object" &&
      "data" in agents &&
      Array.isArray(agents.data)
    ) {
      agentsArray = agents.data;
      console.log("从API响应中提取agents数据:", agentsArray.length);
    }

    if (!Array.isArray(agentsArray)) {
      console.warn("agents is not an array:", agents);
      return [];
    }

    return agentsArray.filter((agent) => {
      // 搜索过滤
      const matchesSearch =
        !searchText ||
        agent.name.toLowerCase().includes(searchText.toLowerCase()) ||
        agent.description?.toLowerCase().includes(searchText.toLowerCase());

      // 可见性过滤 - 处理大小写差异
      const matchesVisibility =
        visibilityFilter === "all" ||
        agent.visibility?.toLowerCase() === visibilityFilter.toLowerCase();

      return matchesSearch && matchesVisibility;
    });
  }, [agents, searchText, visibilityFilter]);

  // 选择/取消选择智能体
  const toggleAgent = useCallback(
    (agentId: string) => {
      const isSelected = selectedAgents.includes(agentId);

      if (isSelected) {
        // 取消选择
        onChange(selectedAgents.filter((id) => id !== agentId));
      } else {
        // 选择智能体
        if (selectedAgents.length >= maxSelection) {
          message.warning(`最多只能选择${maxSelection}个智能体`);
          return;
        }
        onChange([...selectedAgents, agentId]);
      }
    },
    [selectedAgents, onChange, maxSelection],
  );

  // 全选/取消全选
  const handleSelectAll = useCallback(() => {
    if (selectedAgents.length === filteredAgents.length) {
      // 取消全选
      onChange([]);
    } else {
      // 全选（限制数量）
      const allIds = filteredAgents
        .slice(0, maxSelection)
        .map((agent) => agent.id);
      onChange(allIds);
    }
  }, [selectedAgents, filteredAgents, maxSelection, onChange]);

  return (
    <Card
      title={
        <Space>
          <RobotOutlined />
          智能体选择
          <Badge
            count={selectedAgents.length}
            showZero
            style={{ backgroundColor: "#52c41a" }}
          />
          <span style={{ color: "#666", fontSize: "14px" }}>
            (共 {filteredAgents.length} 个)
          </span>
        </Space>
      }
      extra={
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => loadAgents(true)}
            loading={loading}
          >
            刷新
          </Button>
        </Space>
      }
      className="agent-selector"
    >
      {/* 搜索和过滤 */}
      <div style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Search
              placeholder="搜索智能体名称或描述"
              allowClear
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={setSearchText}
            />
          </Col>
          <Col span={8}>
            <Select
              placeholder="筛选可见性"
              style={{ width: "100%" }}
              value={visibilityFilter}
              onChange={setVisibilityFilter}
            >
              <Option value="all">全部</Option>
              <Option value="public">
                <Space>
                  <GlobalOutlined />
                  公开
                </Space>
              </Option>
              <Option value="private">
                <Space>
                  <LockOutlined />
                  私有
                </Space>
              </Option>
            </Select>
          </Col>
          <Col span={4}>
            <Button
              type={selectedAgents.length > 0 ? "default" : "primary"}
              onClick={handleSelectAll}
              disabled={filteredAgents.length === 0}
              block
            >
              {selectedAgents.length === filteredAgents.length &&
              filteredAgents.length > 0
                ? "取消全选"
                : "全选"}
            </Button>
          </Col>
        </Row>
      </div>

      {/* 选择统计 */}
      {selectedAgents.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Tag color="blue">
            已选择 {selectedAgents.length}/{maxSelection} 个智能体
          </Tag>
          {selectedAgents.length >= maxSelection && (
            <Tag color="orange">已达到最大选择数量</Tag>
          )}
        </div>
      )}

      {/* 智能体列表 */}
      {error ? (
        <div style={{ textAlign: "center", padding: "20px" }}>
          <p style={{ color: "#ff4d4f" }}>加载失败: {error}</p>
          <Button onClick={() => loadAgents(true)}>重试</Button>
        </div>
      ) : filteredAgents.length === 0 ? (
        <Empty
          description={searchText ? "没有找到匹配的智能体" : "暂无智能体"}
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <List
          loading={loading}
          dataSource={filteredAgents}
          renderItem={(agent) => {
            const isSelected = selectedAgents.includes(agent.id);
            const canSelect =
              !isSelected && selectedAgents.length < maxSelection;

            return (
              <List.Item
                className={`agent-item ${isSelected ? "selected" : ""}`}
                style={{
                  padding: "12px 16px",
                  border: isSelected
                    ? "2px solid #1890ff"
                    : "1px solid #f0f0f0",
                  borderRadius: "8px",
                  marginBottom: "8px",
                  backgroundColor: isSelected ? "#f6ffed" : "#fff",
                  cursor: canSelect || isSelected ? "pointer" : "not-allowed",
                  opacity: canSelect || isSelected ? 1 : 0.6,
                }}
                onClick={() =>
                  (canSelect || isSelected) && toggleAgent(agent.id)
                }
                actions={[
                  <Tooltip
                    key="checkbox-tooltip"
                    title={
                      isSelected
                        ? "取消选择"
                        : canSelect
                          ? "选择"
                          : "已达到最大选择数量"
                    }
                  >
                    <Checkbox
                      checked={isSelected}
                      disabled={!canSelect && !isSelected}
                      onChange={() =>
                        (canSelect || isSelected) && toggleAgent(agent.id)
                      }
                    />
                  </Tooltip>,
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <AvatarDisplay
                      agent={agent}
                      size={48}
                      style={{
                        border: isSelected ? "2px solid #52c41a" : "none",
                      }}
                    />
                  }
                  title={
                    <Space>
                      <span style={{ fontWeight: 600 }}>{agent.name}</span>
                      <Tag
                        color={
                          agent.visibility?.toLowerCase() === "public"
                            ? "blue"
                            : "orange"
                        }
                        icon={
                          agent.visibility?.toLowerCase() === "public" ? (
                            <GlobalOutlined />
                          ) : (
                            <LockOutlined />
                          )
                        }
                      >
                        {agent.visibility?.toLowerCase() === "public"
                          ? "公开"
                          : "私有"}
                      </Tag>
                      {agent.gender && (
                        <Tag color="default">{agent.gender}</Tag>
                      )}
                      {isSelected && (
                        <CheckCircleOutlined style={{ color: "#52c41a" }} />
                      )}
                    </Space>
                  }
                  description={
                    <div>
                      {agent.description && (
                        <p
                          style={{
                            margin: "4px 0",
                            color: "#666",
                            lineHeight: "1.4",
                          }}
                        >
                          {agent.description}
                        </p>
                      )}
                      <div style={{ fontSize: "12px", color: "#999" }}>
                        创建时间 (UTC): {formatUtcTimeRaw(agent.created_at)}
                      </div>
                    </div>
                  }
                />
              </List.Item>
            );
          }}
        />
      )}
    </Card>
  );
};
