/**
 * 实时语音通话状态管理 Hook
 * CREATED_BY_AGENT
 */

import { useState, useCallback, useRef, useEffect } from "react";
import {
  LiveChatService,
  ConnectionStatus,
  SessionInfo,
  LatencyMetrics,
} from "../services/liveChat";

export interface Transcript {
  role: "user" | "assistant";
  text: string;
  timestamp: Date;
}

export interface UseLiveChatReturn {
  status: ConnectionStatus;
  isRecording: boolean;
  isMuted: boolean;
  transcripts: Transcript[];
  error: { code: string; message: string } | null;
  remainingDuration: number | null;
  elapsedTime: number;
  sessionInfo: SessionInfo | null;
  latencyMetrics: LatencyMetrics;

  startCall: (agentId: string) => Promise<void>;
  endCall: () => void;
  toggleMute: () => void;
  sendText: (text: string) => void;
  clearTranscripts: () => void;
  clearError: () => void;
}

export function useLiveChat(): UseLiveChatReturn {
  const [status, setStatus] = useState<ConnectionStatus>("idle");
  const [isRecording, setIsRecording] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  const [error, setError] = useState<{ code: string; message: string } | null>(
    null,
  );
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [remainingDuration, setRemainingDuration] = useState<number | null>(
    null,
  );
  const [elapsedTime, setElapsedTime] = useState(0);
  const [latencyMetrics, setLatencyMetrics] = useState<LatencyMetrics>({});

  const serviceRef = useRef<LiveChatService | null>(null);
  const agentIdRef = useRef<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const initialRemainingRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (serviceRef.current) {
        serviceRef.current.disconnect();
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const isInCall =
      status === "connected" || status === "speaking" || status === "listening";

    if (isInCall && initialRemainingRef.current !== null && !timerRef.current) {
      startTimeRef.current = Date.now();
      timerRef.current = setInterval(() => {
        const elapsed = Math.floor(
          (Date.now() - (startTimeRef.current || Date.now())) / 1000,
        );
        setElapsedTime(elapsed);

        const newRemaining = Math.max(
          0,
          (initialRemainingRef.current || 0) - elapsed,
        );
        setRemainingDuration(newRemaining);
      }, 1000);
    } else if (!isInCall && timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
      startTimeRef.current = null;
    }
  }, [status]);

  const handleAudioReceived = useCallback((_audioData: ArrayBuffer) => {
    // Audio is automatically played by LiveChatService
    // This callback is for any additional processing if needed
  }, []);

  const handleTranscript = useCallback(
    (text: string, role: "user" | "assistant") => {
      setTranscripts((prev) => [
        ...prev,
        {
          role,
          text,
          timestamp: new Date(),
        },
      ]);
    },
    [],
  );

  const handleStatusChange = useCallback(
    (newStatus: ConnectionStatus, _message?: string) => {
      setStatus(newStatus);
    },
    [],
  );

  const handleError = useCallback((code: string, message: string) => {
    setError({ code, message });
    console.error(`Live chat error [${code}]: ${message}`);
    // 收到错误时停止录音状态
    setIsRecording(false);
  }, []);

  const handleSessionInfo = useCallback((info: SessionInfo) => {
    setSessionInfo(info);
    setRemainingDuration(info.remainingDuration);
    initialRemainingRef.current = info.remainingDuration;
    console.log(
      `会话信息: 剩余 ${info.remainingDuration}s, ` +
        `agent 限制 ${info.agentLimit}, 已聊 ${info.agentCount}`,
    );
  }, []);

  const handleLatencyUpdate = useCallback((metrics: LatencyMetrics) => {
    setLatencyMetrics((prev) => ({
      ...prev,
      ...metrics,
    }));
  }, []);

  const startCall = useCallback(
    async (agentId: string) => {
      // 清理之前的连接（如果有）
      if (serviceRef.current) {
        if (serviceRef.current.isConnected()) {
          console.warn("Already in a call");
          return;
        }
        // 确保旧的 service 被完全清理
        serviceRef.current.disconnect();
        serviceRef.current = null;
      }

      setError(null);
      setStatus("connecting");
      setTranscripts([]);
      setSessionInfo(null);
      setRemainingDuration(null);
      setElapsedTime(0);
      setLatencyMetrics({});
      initialRemainingRef.current = null;
      agentIdRef.current = agentId;

      const service = new LiveChatService();
      serviceRef.current = service;

      try {
        await service.connect(
          { agentId },
          {
            onAudioReceived: handleAudioReceived,
            onTranscript: handleTranscript,
            onStatusChange: handleStatusChange,
            onError: handleError,
            onSessionInfo: handleSessionInfo,
            onLatencyUpdate: handleLatencyUpdate,
          },
        );

        await service.startRecording();
        setIsRecording(true);
        setIsMuted(false);
      } catch (err) {
        console.error("Failed to start call:", err);
        setError({
          code: "START_FAILED",
          message: err instanceof Error ? err.message : "启动通话失败",
        });
        setStatus("error");
      }
    },
    [
      handleAudioReceived,
      handleTranscript,
      handleStatusChange,
      handleError,
      handleSessionInfo,
      handleLatencyUpdate,
    ],
  );

  const endCall = useCallback(() => {
    if (serviceRef.current) {
      serviceRef.current.disconnect();
      serviceRef.current = null;
    }

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    setIsRecording(false);
    setIsMuted(false);
    setStatus("disconnected");
    agentIdRef.current = null;
  }, []);

  const toggleMute = useCallback(() => {
    if (!serviceRef.current) return;

    if (isMuted) {
      serviceRef.current.startRecording().then(() => {
        setIsRecording(true);
        setIsMuted(false);
      });
    } else {
      serviceRef.current.stopRecording();
      setIsRecording(false);
      setIsMuted(true);
    }
  }, [isMuted]);

  const sendText = useCallback((text: string) => {
    if (!serviceRef.current?.isConnected()) {
      console.warn("Not connected");
      return;
    }

    serviceRef.current.sendText(text);

    setTranscripts((prev) => [
      ...prev,
      {
        role: "user",
        text,
        timestamp: new Date(),
      },
    ]);
  }, []);

  const clearTranscripts = useCallback(() => {
    setTranscripts([]);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    status,
    isRecording,
    isMuted,
    transcripts,
    error,
    remainingDuration,
    elapsedTime,
    sessionInfo,
    latencyMetrics,
    startCall,
    endCall,
    toggleMute,
    sendText,
    clearTranscripts,
    clearError,
  };
}
