/**
 * Premium 模式切换组件
 * 从聊天设置中显示当前 premium 模式状态
 */

import React, { useState, useEffect, useCallback } from "react";
import { Button, Tooltip, Spin } from "antd";
import api from "../../services/api";

interface PremiumModeToggleProps {
  agentId?: string;
  onToggle?: (enabled: boolean) => void;
  disabled?: boolean;
}

export const PremiumModeToggle: React.FC<PremiumModeToggleProps> = ({
  agentId,
  onToggle,
  disabled = false,
}) => {
  const [premiumMode, setPremiumMode] = useState<boolean>(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
// 加载 premium 模式状态
  const loadPremiumMode = useCallback(async () => {
    if (!agentId) return;

    setLoading(true);
    setError(null);

    try {
      const settings = await api
        .getIntyClient()
        .api.v1.chats.agents.getSettings(agentId);
      setPremiumMode(settings.premium_mode || false);
    } catch (err) {
      console.error("Failed to load premium mode settings:", err);
      setError("Failed to load premium mode settings");
    } finally {
      setLoading(false);
    }
  }, [agentId]);
// 处理切换
  const handleToggle = async (checked: boolean) => {
    if (!agentId) return;

    setLoading(true);
    setError(null); // Clear any previous errors when user retries

    try {
      console.log("Premium mode toggle requested:", checked);
//调用实际的API来更新聊天设置
      await api.chat.updateAgentSettings(agentId, {
        premium_mode: checked,
      });
//调用在成功调用API后才更新本地状态
      setPremiumMode(checked);

      if (onToggle) {
        onToggle(checked);
      }
    } catch (err) {
      console.error("Failed to update premium mode:", err);
      setError("Failed to update premium mode");
// 如果 API 调用失败，则不更新本地状态
// 按钮仍可点击以重试
    } finally {
      setLoading(false);
    }
  };
// 在挂载时或agentId更改时加载设置
  useEffect(() => {
    if (agentId) {
      loadPremiumMode();
    }
  }, [agentId, loadPremiumMode]);

  if (loading && !premiumMode) {
    return (
      <Button
        icon={<Spin size="small" />}
        disabled
        type="default"
        style={{ width: "80px" }}
      >
        Loading...
      </Button>
    );
  }

  if (error) {
    return (
      <Tooltip title={`Premium Mode Error: ${error}`}>
        <Button
          type={premiumMode ? "primary" : "default"}
          danger
          onClick={() => handleToggle(!premiumMode)}
          loading={loading}
          disabled={disabled}
          style={{ width: "80px" }}
        >
          {premiumMode ? "Premium" : "Standard"}
        </Button>
      </Tooltip>
    );
  }

  return (
    <Tooltip title="切换Premium模式">
      <Button
        type={premiumMode ? "primary" : "default"}
        onClick={() => handleToggle(!premiumMode)}
        loading={loading}
        disabled={disabled}
        style={{ width: "80px" }}
      >
        {premiumMode ? "Premium" : "Standard"}
      </Button>
    </Tooltip>
  );
};

export default PremiumModeToggle;
