/**
 * Premium Mode Toggle Component
 * Shows the current premium mode status from chat settings
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

  // Load premium mode status
  const loadPremiumMode = useCallback(async () => {
    if (!agentId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const settings = await api.inty.api.v1.chats.agents.getSettings(agentId);
      setPremiumMode(settings.premium_mode || false);
    } catch (err) {
      console.error("Failed to load premium mode settings:", err);
      setError("Failed to load premium mode settings");
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  // Handle toggle
  const handleToggle = async (checked: boolean) => {
    if (!agentId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Note: The current API doesn't have an update settings endpoint
      // This is a read-only display for now
      console.log("Premium mode toggle requested:", checked);
      
      // For now, just update local state
      setPremiumMode(checked);
      
      if (onToggle) {
        onToggle(checked);
      }
      
      // TODO: Implement actual API call when backend supports updating chat settings
      // await api.inty.api.v1.chats.agents.updateSettings(agentId, { premium_mode: checked });
      
    } catch (err) {
      console.error("Failed to update premium mode:", err);
      setError("Failed to update premium mode");
    } finally {
      setLoading(false);
    }
  };

  // Load settings on mount or when agentId changes
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
        style={{ width: '80px' }}
      >
        Loading...
      </Button>
    );
  }

  if (error) {
    return (
      <Tooltip title={`Premium Mode Error: ${error}`}>
        <Button
          type="default"
          danger
          disabled
          style={{ width: '80px' }}
        >
          Premium
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
        style={{ width: '80px' }}
      >
        {premiumMode ? "Premium" : "Standard"}
      </Button>
    </Tooltip>
  );
};

export default PremiumModeToggle;
