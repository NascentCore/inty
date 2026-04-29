/**
 * Ops-site detail view for a voice recording opened via #voice-recording?… hash route.
 * Permanent links from analytics point here instead of raw GCS URLs.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Button, Card, Descriptions, Empty, Space, Typography } from "antd";
import { SoundOutlined } from "@ant-design/icons";
import { parseEvaluationHashRoute } from "../utils/profileLinks";
import { formatUtcTime } from "../utils/dateUtils";
import {
  OpsAgentDetailModal,
  OpsUserDetailModal,
} from "../components/common/OpsEntityDetailModals";

const { Text, Title } = Typography;

export type ParsedVoiceRecordingRoute = {
  audioUrl: string;
  userId: string;
  agentId: string;
  agentName: string | null;
  createdAt: string | null;
  durationSeconds: number | null;
  messageId: number | null;
};

export function parseVoiceRecordingHash(hash: string): ParsedVoiceRecordingRoute | null {
  const { pageKey, params } = parseEvaluationHashRoute(hash);
  if (pageKey !== "voice-recording") {
    return null;
  }
  const audioUrl = params.get("audioUrl")?.trim() ?? "";
  const userId = params.get("userId")?.trim() ?? "";
  const agentId = params.get("agentId")?.trim() ?? "";
  if (!audioUrl || !userId || !agentId) {
    return null;
  }
  const messageIdRaw = params.get("messageId");
  const messageId =
    messageIdRaw != null && messageIdRaw !== ""
      ? Number.parseInt(messageIdRaw, 10)
      : null;
  const durationRaw = params.get("durationSeconds");
  let durationSeconds: number | null = null;
  if (durationRaw != null && durationRaw !== "") {
    const n = Number.parseFloat(durationRaw);
    durationSeconds = Number.isFinite(n) ? n : null;
  }
  const agentNameRaw = params.get("agentName");
  return {
    audioUrl,
    userId,
    agentId,
    agentName:
      agentNameRaw != null && agentNameRaw !== "" ? agentNameRaw : null,
    createdAt: params.get("createdAt")?.trim() || null,
    durationSeconds,
    messageId: messageId != null && !Number.isNaN(messageId) ? messageId : null,
  };
}

function readVoiceRecordingFromWindow(): ParsedVoiceRecordingRoute | null {
  if (typeof window === "undefined") {
    return null;
  }
  return parseVoiceRecordingHash(window.location.hash);
}

export const VoiceRecordingPage: React.FC = () => {
  const [parsed, setParsed] = useState<ParsedVoiceRecordingRoute | null>(
    readVoiceRecordingFromWindow,
  );
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [agentModalOpen, setAgentModalOpen] = useState(false);

  const readHash = useCallback(() => {
    setParsed(readVoiceRecordingFromWindow());
  }, []);

  useEffect(() => {
    readHash();
    window.addEventListener("hashchange", readHash);
    return () => window.removeEventListener("hashchange", readHash);
  }, [readHash]);

  const durationLabel = useMemo(() => {
    if (parsed?.durationSeconds == null) {
      return "—";
    }
    return `${parsed.durationSeconds.toFixed(1)} s`;
  }, [parsed?.durationSeconds]);

  if (!parsed) {
    return (
      <div style={{ padding: 24 }}>
        <Card>
          <Empty description="无效的录音链接：缺少 audioUrl、userId 或 agentId。" />
        </Card>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 720 }}>
      <Title level={4} style={{ marginTop: 0 }}>
        <SoundOutlined /> 语音通话录音
      </Title>
      <Card>
        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label="录制时间 (UTC)">
            {formatUtcTime(parsed.createdAt)}
          </Descriptions.Item>
          <Descriptions.Item label="用户 ID">
            <Button
              type="link"
              style={{ padding: 0, height: "auto", fontFamily: "monospace" }}
              onClick={() => setUserModalOpen(true)}
            >
              {parsed.userId}
            </Button>
          </Descriptions.Item>
          <Descriptions.Item label="角色">
            {parsed.agentName ?? "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Agent ID">
            <Button
              type="link"
              style={{ padding: 0, height: "auto", fontFamily: "monospace" }}
              onClick={() => setAgentModalOpen(true)}
            >
              {parsed.agentId}
            </Button>
          </Descriptions.Item>
          <Descriptions.Item label="消息 ID">
            {parsed.messageId != null ? String(parsed.messageId) : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="时长">{durationLabel}</Descriptions.Item>
        </Descriptions>

        <div style={{ marginTop: 16 }}>
          <Text type="secondary">试听</Text>
          <audio
            src={parsed.audioUrl}
            controls
            preload="metadata"
            style={{
              display: "block",
              width: "100%",
              maxWidth: 480,
              marginTop: 8,
              height: 36,
            }}
          />
        </div>

        <Space direction="vertical" size="small" style={{ marginTop: 16 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            音频文件地址（运维排查用）
          </Text>
          <Text
            copyable={{ text: parsed.audioUrl }}
            style={{ fontSize: 11, fontFamily: "monospace", wordBreak: "break-all" }}
          >
            {parsed.audioUrl}
          </Text>
        </Space>
      </Card>

      <OpsUserDetailModal
        open={userModalOpen}
        userId={parsed.userId}
        onClose={() => setUserModalOpen(false)}
      />
      <OpsAgentDetailModal
        open={agentModalOpen}
        agentId={parsed.agentId}
        onClose={() => setAgentModalOpen(false)}
      />
    </div>
  );
};
