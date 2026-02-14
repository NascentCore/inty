/**
 * 评测会话管理Hook
 * 提供评测会话的创建、监控、管理功能
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { message } from "antd";
import api, { WebSocketManager } from "../services/api";
import type {
  EvaluationSession,
  EvaluationSessionCreateRequest,
  EvaluationResult,
  WebSocketMessage,
  UseEvaluationSessionOptions,
} from "../types";

interface UseEvaluationSessionReturn {
  // 状态
  session: EvaluationSession | null;
  results: EvaluationResult[];
  loading: boolean;
  error: string | null;

  // 操作
  createSession: (
    data: EvaluationSessionCreateRequest,
  ) => Promise<EvaluationSession | null>;
  startSession: (sessionId: string) => Promise<boolean>;
  cancelSession: (sessionId: string) => Promise<boolean>;
  refreshSession: (sessionId: string) => Promise<void>;
  refreshResults: (sessionId: string) => Promise<void>;

  // WebSocket
  connectWebSocket: (sessionId: string) => Promise<void>;
  disconnectWebSocket: () => void;
  isWebSocketConnected: boolean;
}

export const useEvaluationSession = (
  options: UseEvaluationSessionOptions = {},
): UseEvaluationSessionReturn => {
  const { autoRefresh = false, refreshInterval = 10000 } = options;

  // 状态管理
  const [session, setSession] = useState<EvaluationSession | null>(null);
  const [results, setResults] = useState<EvaluationResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isWebSocketConnected, setIsWebSocketConnected] = useState(false);

  // Refs
  const wsManager = useRef<WebSocketManager | null>(null);
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // 断开WebSocket
  const disconnectWebSocket = useCallback(() => {
    if (wsManager.current) {
      wsManager.current.disconnect();
      wsManager.current = null;
    }
    setIsWebSocketConnected(false);
  }, []);

  // 清理函数
  useEffect(() => {
    return () => {
      if (refreshTimer.current) {
        clearInterval(refreshTimer.current);
      }
      disconnectWebSocket();
    };
  }, [disconnectWebSocket]);

  // 错误处理
  const handleError = useCallback((error: unknown, defaultMessage: string) => {
    const errorMessage =
      error instanceof Error ? error.message : defaultMessage;
    setError(errorMessage);
    message.error(errorMessage);
    console.error(defaultMessage, error);
  }, []);

  // 创建评测会话
  const createSession = useCallback(
    async (
      data: EvaluationSessionCreateRequest,
    ): Promise<EvaluationSession | null> => {
      try {
        setLoading(true);
        setError(null);

        const newSession = await api.sessions.create(data);
        setSession(newSession);

        message.success("评测会话创建成功");
        return newSession;
      } catch (error) {
        handleError(error, "创建评测会话失败");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [handleError],
  );

  // 启动评测会话
  const startSession = useCallback(
    async (sessionId: string): Promise<boolean> => {
      try {
        setLoading(true);
        setError(null);

        const response = await api.sessions.start(sessionId);

        if (response.success) {
          // 更新会话状态
          if (session && session.id === sessionId) {
            setSession((prev) =>
              prev ? { ...prev, status: "running" } : null,
            );
          }

          message.success("评测会话已启动");
          return true;
        } else {
          throw new Error(response.message || "启动失败");
        }
      } catch (error) {
        handleError(error, "启动评测会话失败");
        return false;
      } finally {
        setLoading(false);
      }
    },
    [session, handleError],
  );

  // 取消评测会话
  const cancelSession = useCallback(
    async (sessionId: string): Promise<boolean> => {
      try {
        setLoading(true);
        setError(null);

        const response = await api.sessions.cancel(sessionId);

        if (response.success) {
          // 更新会话状态
          if (session && session.id === sessionId) {
            setSession((prev) =>
              prev ? { ...prev, status: "cancelled" } : null,
            );
          }

          message.success("评测会话已取消");
          return true;
        } else {
          throw new Error(response.message || "取消失败");
        }
      } catch (error) {
        handleError(error, "取消评测会话失败");
        return false;
      } finally {
        setLoading(false);
      }
    },
    [session, handleError],
  );

  // 刷新会话信息
  const refreshSession = useCallback(
    async (sessionId: string) => {
      try {
        const updatedSession = await api.sessions.get(sessionId);
        setSession(updatedSession);
      } catch (error) {
        handleError(error, "刷新会话信息失败");
      }
    },
    [handleError],
  );

  // 刷新评测结果
  const refreshResults = useCallback(
    async (sessionId: string) => {
      try {
        const updatedResults = await api.sessions.getResults(sessionId);
        setResults(updatedResults);
      } catch (error) {
        handleError(error, "刷新评测结果失败");
      }
    },
    [handleError],
  );

  // 连接WebSocket
  const connectWebSocket = useCallback(
    async (sessionId: string) => {
      try {
        // 断开之前的连接
        disconnectWebSocket();

        wsManager.current = new WebSocketManager(sessionId);

        // 设置消息监听器
        wsManager.current.on("session_started", (message: WebSocketMessage) => {
          console.log("评测会话已启动:", message);
          refreshSession(sessionId);
        });

        wsManager.current.on("test_started", (message: WebSocketMessage) => {
          console.log("测试开始:", message);
          // 可以更新UI显示当前测试进度
        });

        wsManager.current.on("test_completed", (message: WebSocketMessage) => {
          console.log("测试完成:", message);
          // 更新结果列表
          refreshResults(sessionId);
          refreshSession(sessionId);
        });

        wsManager.current.on(
          "session_completed",
          (_message: WebSocketMessage) => {
            console.log("评测会话完成:", _message);
            message.success("评测已完成");
            refreshSession(sessionId);
            refreshResults(sessionId);
          },
        );

        wsManager.current.on("session_failed", (_message: WebSocketMessage) => {
          console.log("评测会话失败:", _message);
          message.error("评测执行失败");
          refreshSession(sessionId);
        });

        wsManager.current.on(
          "session_cancelled",
          (_message: WebSocketMessage) => {
            console.log("评测会话取消:", _message);
            message.info("评测已取消");
            refreshSession(sessionId);
          },
        );

        // 连接WebSocket
        await wsManager.current.connect();
        setIsWebSocketConnected(true);
      } catch (error) {
        console.error("WebSocket连接失败:", error);
        setIsWebSocketConnected(false);
      }
    },
    [disconnectWebSocket, refreshSession, refreshResults],
  );

  // 自动刷新 - 扩展到所有非最终状态，增强频率
  useEffect(() => {
    if (
      autoRefresh &&
      session &&
      ["pending", "running"].includes(session.status)
    ) {
      // 运行中的会话更频繁刷新
      const interval = session.status === "running" ? 3000 : refreshInterval;

      refreshTimer.current = setInterval(() => {
        console.log(
          `自动刷新评测会话状态: ${session.id}, 当前状态: ${session.status}`,
        );
        refreshSession(session.id);
        refreshResults(session.id);
      }, interval);

      return () => {
        if (refreshTimer.current) {
          clearInterval(refreshTimer.current);
        }
      };
    }
  }, [autoRefresh, session, refreshInterval, refreshSession, refreshResults]);

  return {
    // 状态
    session,
    results,
    loading,
    error,

    // 操作
    createSession,
    startSession,
    cancelSession,
    refreshSession,
    refreshResults,

    // WebSocket
    connectWebSocket,
    disconnectWebSocket,
    isWebSocketConnected,
  };
};
