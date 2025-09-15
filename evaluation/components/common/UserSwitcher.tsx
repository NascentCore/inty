/**
 * 用户切换组件
 * 提供管理员用户之间的切换功能
 */

import React from "react";
import { Dropdown, Button, Space, Typography, Badge, Tooltip, Spin } from "antd";
import { 
  UserSwitchOutlined, 
  CheckOutlined, 
  LoadingOutlined,
  ExclamationCircleOutlined 
} from "@ant-design/icons";
import { useUserSwitch } from "../auth/UserSwitchProvider";

const { Text } = Typography;

export const UserSwitcher: React.FC = () => {
  const { 
    currentUser, 
    availableUsers, 
    switchUser, 
    loading, 
    error 
  } = useUserSwitch();

  // 生成下拉菜单项
  const menuItems = availableUsers.map((user) => ({
    key: user.id,
    label: (
      <div style={{ 
        display: "flex", 
        alignItems: "center", 
        justifyContent: "space-between",
        padding: "4px 0",
        minWidth: "200px"
      }}>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <Text strong style={{ fontSize: "14px" }}>
            {user.name}
          </Text>
          <Text type="secondary" style={{ fontSize: "12px" }}>
            {user.description}
          </Text>
        </div>
        {currentUser?.id === user.id && (
          <CheckOutlined style={{ color: "#52c41a", fontSize: "16px" }} />
        )}
      </div>
    ),
    onClick: () => switchUser(user.id),
  }));

  // 获取当前用户显示信息
  const getCurrentUserDisplay = () => {
    if (loading) {
      return (
        <Space size="small">
          <Spin size="small" />
          <Text type="secondary">切换中...</Text>
        </Space>
      );
    }

    if (error) {
      return (
        <Tooltip title={`切换失败: ${error}`}>
          <Space size="small">
            <ExclamationCircleOutlined style={{ color: "#ff4d4f" }} />
            <Text type="danger">切换失败</Text>
          </Space>
        </Tooltip>
      );
    }

    if (!currentUser) {
      return (
        <Space size="small">
          <UserSwitchOutlined />
          <Text type="secondary">未选择用户</Text>
        </Space>
      );
    }

    return (
      <Space size="small">
        <UserSwitchOutlined />
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
          <Text strong style={{ fontSize: "12px", lineHeight: "1.2" }}>
            {currentUser.name}
          </Text>
          <Text type="secondary" style={{ fontSize: "10px", lineHeight: "1.2" }}>
            {currentUser.description}
          </Text>
        </div>
      </Space>
    );
  };

  return (
    <Dropdown
      menu={{ items: menuItems }}
      placement="bottomRight"
      trigger={["click"]}
      disabled={loading}
    >
      <Button
        type="text"
        size="small"
        style={{
          height: "auto",
          padding: "4px 8px",
          borderRadius: "6px",
          border: "1px solid #d9d9d9",
          background: error ? "#fff2f0" : loading ? "#f5f5f5" : "#fff",
          color: error ? "#ff4d4f" : "#666",
        }}
        onMouseEnter={(e) => {
          if (!loading && !error) {
            e.currentTarget.style.backgroundColor = "#f5f5f5";
            e.currentTarget.style.borderColor = "#1890ff";
          }
        }}
        onMouseLeave={(e) => {
          if (!loading && !error) {
            e.currentTarget.style.backgroundColor = "#fff";
            e.currentTarget.style.borderColor = "#d9d9d9";
          }
        }}
      >
        {getCurrentUserDisplay()}
      </Button>
    </Dropdown>
  );
};

export default UserSwitcher;
