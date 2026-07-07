/**
 * Chat Mode selector: shows the three user-facing modes (Flirt, Story, Vivid) when
 * the agent default is one of them. When agent default is not in the three, nothing is shown.
 */

import React, { useCallback, useEffect, useState } from "react";
import { Select, Spin, Tooltip } from "antd";
import api from "../../services/api";

export interface ChatModeOption {
  id: string;
  short_name: string;
  name: string;
  description: string;
}

interface ChatModeSelectorProps {
  agentId?: string;
  onModeChange?: (modeId: string | null) => void;
  disabled?: boolean;
}

export const ChatModeSelector: React.FC<ChatModeSelectorProps> = ({
  agentId,
  onModeChange,
  disabled = false,
}) => {
  const [chatMode, setChatMode] = useState<string | null>(null);
  const [availableModes, setAvailableModes] = useState<ChatModeOption[]>([]);
  const [loading, setLoading] = useState(false);

  const loadSettings = useCallback(async () => {
    if (!agentId) return;
    setLoading(true);
    try {
      const [settings, modes] = await Promise.all([
        api.chat.getAgentSettings(agentId) as {
          chat_mode?: string | null;
        },
        api.chat.getModes(agentId),
      ]);
      setChatMode(settings.chat_mode ?? null);
      setAvailableModes(Array.isArray(modes) ? modes : []);
    } catch (err) {
      console.error("Failed to load chat mode settings:", err);
      setAvailableModes([]);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    if (agentId) loadSettings();
    else {
      setAvailableModes([]);
      setChatMode(null);
    }
  }, [agentId, loadSettings]);

  const handleChange = async (value: string) => {
    if (!agentId) return;
    setLoading(true);
    try {
      await api.chat.updateAgentSettings(agentId, { chat_mode: value });
      setChatMode(value);
      onModeChange?.(value);
    } catch (err) {
      console.error("Failed to update chat mode:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading && availableModes.length === 0) {
    return (
      <Select
        placeholder="Mode..."
        style={{ width: 100 }}
        disabled
        suffixIcon={<Spin size="small" />}
      />
    );
  }
  if (availableModes.length === 0) return null;

  return (
    <Tooltip title="Chat mode: Flirt / Story / Vivid">
      <Select
        value={chatMode ?? undefined}
        placeholder="Mode"
        style={{ width: 110 }}
        onChange={handleChange}
        disabled={disabled}
        options={availableModes.map((m) => ({
          value: m.id,
          label: m.short_name || m.name,
        }))}
      />
    </Tooltip>
  );
};

export default ChatModeSelector;
