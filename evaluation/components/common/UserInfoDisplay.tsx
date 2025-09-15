/**
 * 用户信息显示组件
 * 显示在页面右上角的用户信息
 */

import React from "react";
import { Avatar, Dropdown, Typography, Space, Badge, Tooltip } from "antd";
import {
  UserOutlined,
  SettingOutlined,
  CrownOutlined,
} from "@ant-design/icons";
import { UserProfile } from "../../hooks/useUser";

const { Text } = Typography;

interface UserInfoDisplayProps {
  user: UserProfile | null;
  loading?: boolean;
}

export const UserInfoDisplay: React.FC<UserInfoDisplayProps> = ({
  user,
  loading = false,
}) => {
  // 生成用户头像
  const getUserAvatar = () => {
    if (user?.avatar) {
      return <Avatar src={user.avatar} size="small" />;
    }
    return <Avatar icon={<UserOutlined />} size="small" />;
  };

  // 生成用户显示名称
  const getUserDisplayName = () => {
    if (!user) return "未知用户";
    return user.nickname || user.readable_id || "用户";
  };

  // 生成用户状态徽章
  const getUserStatusBadge = () => {
    if (!user) return null;
    
    if (user.is_superuser) {
      return (
        <Tooltip title="超级管理员">
          <Badge 
            count={<CrownOutlined style={{ color: "#ffd700", fontSize: "10px" }} />}
            offset={[-2, 2]}
          >
            <div />
          </Badge>
        </Tooltip>
      );
    }
    
    if (!user.is_active) {
      return (
        <Tooltip title="账户未激活">
          <Badge status="error" />
        </Tooltip>
      );
    }
    
    return (
      <Tooltip title="在线">
        <Badge status="success" />
      </Tooltip>
    );
  };

  // 下拉菜单项
  const menuItems = [
    {
      key: "profile",
      icon: <UserOutlined />,
      label: "个人资料",
      onClick: () => {
        console.log("查看个人资料");
        // TODO: 实现个人资料页面跳转
      },
    },
    {
      key: "settings",
      icon: <SettingOutlined />,
      label: "设置",
      onClick: () => {
        console.log("打开设置");
        // TODO: 实现设置页面跳转
      },
    },
  ];

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <Avatar size="small" />
        <Text type="secondary">加载中...</Text>
      </div>
    );
  }

  if (!user) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <Avatar icon={<UserOutlined />} size="small" />
        <Text type="secondary">未登录</Text>
      </div>
    );
  }

  return (
    <Dropdown
      menu={{ items: menuItems }}
      placement="bottomRight"
      trigger={["click"]}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          cursor: "pointer",
          padding: "4px 8px",
          borderRadius: "6px",
          transition: "background-color 0.2s",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = "#f5f5f5";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = "transparent";
        }}
      >
        <Space size="small">
          {getUserStatusBadge()}
          {getUserAvatar()}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
            <Text strong style={{ fontSize: "14px", lineHeight: "1.2" }}>
              {getUserDisplayName()}
            </Text>
            <Text type="secondary" style={{ fontSize: "12px", lineHeight: "1.2" }}>
              {user.readable_id}
            </Text>
          </div>
        </Space>
      </div>
    </Dropdown>
  );
};
