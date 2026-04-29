import React, { useEffect, useState } from "react";
import { Button, Descriptions, Modal, Spin, Typography } from "antd";
import { LinkOutlined } from "@ant-design/icons";
import { agentApi, userAnalyticsApi } from "../../services/api";
import type { Agent, UserDailyMessagesResponse } from "../../types";
import { AgentInfoDisplay } from "./AgentInfoDisplay";
import {
  buildAgentProfilePageUrl,
  buildUserProfilePageUrl,
  getEvaluationBaseUrl,
} from "../../utils/profileLinks";

const { Text } = Typography;

export const OpsUserDetailModal: React.FC<{
  open: boolean;
  userId: string;
  onClose: () => void;
}> = ({ open, userId, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userInfo, setUserInfo] = useState<UserDailyMessagesResponse | null>(
    null,
  );

  useEffect(() => {
    if (!open || !userId.trim()) {
      return;
    }
    setLoading(true);
    setError(null);
    setUserInfo(null);
    userAnalyticsApi
      .getUserDailyMessages({ user_id: userId.trim() })
      .then((data) => {
        setUserInfo(data);
      })
      .catch((err: unknown) => {
        const msg =
          err instanceof Error ? err.message : "Failed to load user details";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, [open, userId]);

  const baseUrl = getEvaluationBaseUrl();
  const profileUrl = buildUserProfilePageUrl(baseUrl, userId);

  return (
    <Modal
      title="用户详情"
      open={open}
      onCancel={onClose}
      footer={
        <Button type="primary" onClick={onClose}>
          关闭
        </Button>
      }
      width={560}
      destroyOnHidden
    >
      {loading ? (
        <div style={{ textAlign: "center", padding: 24 }}>
          <Spin />
        </div>
      ) : error ? (
        <Text type="danger">{error}</Text>
      ) : userInfo ? (
        <>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="用户 ID">
              <Text copyable={{ text: userInfo.user_id }} style={{ fontFamily: "monospace" }}>
                {userInfo.user_id}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="邮箱">
              {userInfo.email ?? "—"}
            </Descriptions.Item>
            <Descriptions.Item label="昵称">
              {userInfo.nickname ?? "—"}
            </Descriptions.Item>
            <Descriptions.Item label="认证方式">
              {userInfo.auth_type}
            </Descriptions.Item>
            <Descriptions.Item label="注册时间 (UTC)">
              {userInfo.created_at ?? "—"}
            </Descriptions.Item>
          </Descriptions>
          <div style={{ marginTop: 16 }}>
            <a href={profileUrl} target="_blank" rel="noopener noreferrer">
              <LinkOutlined /> 在用户每日消息中打开
            </a>
          </div>
        </>
      ) : null}
    </Modal>
  );
};

export const OpsAgentDetailModal: React.FC<{
  open: boolean;
  agentId: string;
  onClose: () => void;
}> = ({ open, agentId, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agent, setAgent] = useState<Agent | null>(null);

  useEffect(() => {
    if (!open || !agentId.trim()) {
      return;
    }
    setLoading(true);
    setError(null);
    setAgent(null);
    agentApi
      .get(agentId.trim())
      .then((data) => setAgent(data))
      .catch((err: unknown) => {
        const msg =
          err instanceof Error ? err.message : "Failed to load agent details";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, [open, agentId]);

  const baseUrl = getEvaluationBaseUrl();
  const profileUrl = buildAgentProfilePageUrl(baseUrl, agentId);

  return (
    <Modal
      title={agent ? `角色详情 · ${agent.name}` : "角色详情"}
      open={open}
      onCancel={onClose}
      footer={
        <Button type="primary" onClick={onClose}>
          关闭
        </Button>
      }
      width={800}
      style={{ top: 24 }}
      destroyOnHidden
    >
      {loading ? (
        <div style={{ textAlign: "center", padding: 48 }}>
          <Spin size="large" />
        </div>
      ) : error ? (
        <>
          <Text type="danger">{error}</Text>
          <div style={{ marginTop: 16 }}>
            <a href={profileUrl} target="_blank" rel="noopener noreferrer">
              <LinkOutlined /> 在智能体管理中打开
            </a>
          </div>
        </>
      ) : agent ? (
        <>
          <AgentInfoDisplay agent={agent} compact />
          <div style={{ marginTop: 16 }}>
            <a href={profileUrl} target="_blank" rel="noopener noreferrer">
              <LinkOutlined /> 在智能体管理中打开
            </a>
          </div>
        </>
      ) : null}
    </Modal>
  );
};
