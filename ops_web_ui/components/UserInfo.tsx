/**
 * 用户信息显示组件
 * 显示当前 API Key 对应的用户信息
 */

import React, { useState, useEffect, useCallback } from "react";
import { Avatar, Dropdown, Typography, Space } from "antd";
import { UserOutlined, KeyOutlined } from "@ant-design/icons";
import { useApiKeyContext } from "../hooks/useApiKey";
import api from "../services/api";
import { userDisplayId } from "../utils/userDisplayId";

const { Text } = Typography;

interface UserProfile {
  id: string;
  readable_id?: string | null;
  nickname?: string | null;
  avatar?: string | null;
  email?: string | null;
  is_superuser?: boolean;
}

interface UserInfoProps {
  onShowApiKeyModal: () => void;
}

export const UserInfo: React.FC<UserInfoProps> = ({ onShowApiKeyModal }) => {
  const [userInfo, setUserInfo] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const { isApiKeyValid } = useApiKeyContext();

  // 获取用户信息
  const fetchUserInfo = useCallback(async () => {
    if (!isApiKeyValid) {
      setUserInfo(null);
      return;
    }

    try {
      setLoading(true);
      const response = (await api.users.me()) as unknown as UserProfile | null;
      setUserInfo(response || null);
    } catch (error) {
      console.error("获取用户信息失败:", error);
      setUserInfo(null);
    } finally {
      setLoading(false);
    }
  }, [isApiKeyValid]);

  // 当 API Key 状态变化时重新获取用户信息
  useEffect(() => {
    fetchUserInfo();
  }, [fetchUserInfo]);

  // 如果没有 API Key 或正在加载，不显示组件
  if (!isApiKeyValid || loading) {
    return null;
  }

  // 如果没有用户信息，显示默认状态
  if (!userInfo) {
    return (
      <div style={{ padding: "0 16px" }}>
        <Text type="secondary">用户信息加载中...</Text>
      </div>
    );
  }

  const displayId = userDisplayId(userInfo);

  const menuItems = [
    {
      key: "profile",
      label: (
        <div style={{ padding: "8px 0" }}>
          <div style={{ fontWeight: 500, marginBottom: "4px" }}>
            {userInfo.nickname || displayId}
          </div>
          <div style={{ fontSize: "12px", color: "#666" }}>
            {userInfo.email || displayId}
          </div>
          <div style={{ fontSize: "12px", color: "#999", marginTop: "2px" }}>
            ID: {userInfo.id}
          </div>
          {userInfo.is_superuser && (
            <div
              style={{ fontSize: "12px", color: "#1890ff", marginTop: "2px" }}
            >
              管理员
            </div>
          )}
        </div>
      ),
    },
    {
      type: "divider" as const,
    },
    {
      key: "api-key-status",
      label: (
        <div style={{ padding: "4px 0" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              marginBottom: "4px",
            }}
          >
            <KeyOutlined
              style={{
                marginRight: "8px",
                color: isApiKeyValid ? "#52c41a" : "#ff4d4f",
              }}
            />
            <span style={{ fontSize: "14px" }}>
              {isApiKeyValid ? "API Key 已设置" : "API Key 未设置"}
            </span>
          </div>
          <div style={{ fontSize: "12px", color: "#666", marginLeft: "24px" }}>
            {isApiKeyValid
              ? "点击下方按钮重新设置"
              : "点击下方按钮设置 API Key"}
          </div>
        </div>
      ),
    },
    {
      key: "set-api-key",
      label: (
        <Space>
          <KeyOutlined />
          {isApiKeyValid ? "重新设置 API Key" : "设置 API Key"}
        </Space>
      ),
      onClick: onShowApiKeyModal,
    },
  ];

  return (
    <div style={{ padding: "0 16px" }}>
      <Dropdown
        menu={{ items: menuItems }}
        placement="bottomRight"
        trigger={["click"]}
      >
        <div
          style={{ cursor: "pointer", display: "flex", alignItems: "center" }}
        >
          <Avatar
            size="small"
            src={userInfo.avatar}
            icon={<UserOutlined />}
            style={{ marginRight: "8px" }}
          />
          <div>
            <div style={{ fontSize: "14px", fontWeight: 500, lineHeight: 1.2 }}>
              {userInfo.nickname || displayId}
            </div>
            <div style={{ fontSize: "12px", color: "#666", lineHeight: 1.2 }}>
              {userInfo.is_superuser ? "管理员" : "用户"}
            </div>
          </div>
        </div>
      </Dropdown>
    </div>
  );
};
