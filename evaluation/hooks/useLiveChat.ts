/**
 * 实时语音通话状态管理 Hook
 * CREATED_BY_AGENT
 */

import { useState, useCallback, useRef, useEffect } from "react";
import {
  LiveChatService,
  LiveChatConfig,
  ConnectionStatus,
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

  startCall: (
    agentId: string,
    config?: Partial<LiveChatConfig>
  ) => Promise<void>;
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
    null
  );

  const serviceRef = useRef<LiveChatService | null>(null);
  const agentIdRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      if (serviceRef.current) {
        serviceRef.current.disconnect();
      }
    };
  }, []);

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
    []
  );

  const handleStatusChange = useCallback(
    (newStatus: ConnectionStatus, _message?: string) => {
      setStatus(newStatus);
    },
    []
  );

  const handleError = useCallback((code: string, message: string) => {
    setError({ code, message });
    console.error(`Live chat error [${code}]: ${message}`);
  }, []);

  const startCall = useCallback(
    async (agentId: string, config?: Partial<LiveChatConfig>) => {
      if (serviceRef.current?.isConnected()) {
        console.warn("Already in a call");
        return;
      }

      setError(null);
      setTranscripts([]);
      agentIdRef.current = agentId;

      const service = new LiveChatService();
      serviceRef.current = service;

      try {
        await service.connect(
          {
            agentId,
            saveHistory: config?.saveHistory ?? true,
            voiceId: config?.voiceId,
          },
          {
            onAudioReceived: handleAudioReceived,
            onTranscript: handleTranscript,
            onStatusChange: handleStatusChange,
            onError: handleError,
          }
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
    [handleAudioReceived, handleTranscript, handleStatusChange, handleError]
  );

  const endCall = useCallback(() => {
    if (serviceRef.current) {
      serviceRef.current.disconnect();
      serviceRef.current = null;
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
    startCall,
    endCall,
    toggleMute,
    sendText,
    clearTranscripts,
    clearError,
  };
}

