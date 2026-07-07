/**
 * 语音播放组件
 * 支持语音生成、缓存和播放功能
 */

import React, { useState, useRef, useEffect } from "react";
import { Button, Tooltip, message } from "antd";
import {
  SoundOutlined,
  LoadingOutlined,
  PauseOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";
import { chatApi } from "../../services/api";

interface VoicePlayerProps {
  // 智能体ID
  agentId: string;
  // 消息ID
  messageId: string;
  // 消息文本内容
  messageText: string;
  // 语言设置
  language?: string;
  // 样式控制
  size?: "small" | "middle" | "large";
  // 是否显示文字
  showText?: boolean;
  // 自定义样式
  style?: React.CSSProperties;
  // 播放状态变化回调
  onPlayStateChange?: (isPlaying: boolean) => void;
}

// 全局音频管理器 - 确保同时只有一个音频在播放
class GlobalAudioManager {
  private currentAudio: HTMLAudioElement | null = null;
  private currentPlayerId: string | null = null;
  private listeners: Map<string, (isPlaying: boolean) => void> = new Map();

  play(audio: HTMLAudioElement, playerId: string): void {
    // 停止当前播放的音频
    if (this.currentAudio && this.currentAudio !== audio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;

      // 通知之前的播放器状态变化
      if (this.currentPlayerId) {
        const prevListener = this.listeners.get(this.currentPlayerId);
        if (prevListener) {
          prevListener(false);
        }
      }
    }

    this.currentAudio = audio;
    this.currentPlayerId = playerId;
    audio.play();
  }

  stop(playerId: string): void {
    if (this.currentPlayerId === playerId && this.currentAudio) {
      try {
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
      } catch (e) {
        // 忽略停止时的错误，可能是组件已卸载
      }
      this.currentAudio = null;
      this.currentPlayerId = null;
    }
  }

  isCurrentPlayer(playerId: string): boolean {
    return this.currentPlayerId === playerId;
  }

  registerListener(
    playerId: string,
    listener: (isPlaying: boolean) => void,
  ): void {
    this.listeners.set(playerId, listener);
  }

  unregisterListener(playerId: string): void {
    this.listeners.delete(playerId);
  }
}

const globalAudioManager = new GlobalAudioManager();

export const VoicePlayer: React.FC<VoicePlayerProps> = ({
  agentId,
  messageId,
  language = "zh",
  size = "small",
  showText = false,
  style,
  onPlayStateChange,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [hasError, setHasError] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const playerId = useRef(`${agentId}-${messageId}`).current;
  const isUnmountedRef = useRef(false);

  // 注册全局音频管理器监听
  useEffect(() => {
    const handleGlobalPlayStateChange = (playing: boolean) => {
      if (!playing && isPlaying) {
        setIsPlaying(false);
        onPlayStateChange?.(false);
      }
    };

    globalAudioManager.registerListener(playerId, handleGlobalPlayStateChange);

    return () => {
      globalAudioManager.unregisterListener(playerId);
    };
  }, [playerId, isPlaying, onPlayStateChange]);

  // 生成语音
  const generateVoice = async (): Promise<string> => {
    try {
      setIsLoading(true);
      setHasError(false);

      const response = await chatApi.generateVoice(
        agentId,
        messageId,
        language,
      );

      if (!response.audio_url) {
        throw new Error("语音生成失败：未返回音频URL");
      }

      setAudioUrl(response.audio_url);
      return response.audio_url;
    } catch (error) {
      console.error("语音生成失败:", error);
      setHasError(true);
      message.error("语音生成失败，请稍后重试");
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // 播放语音
  const playVoice = async () => {
    try {
      let urlToPlay = audioUrl;

      // 如果没有缓存的音频URL，先生成
      if (!urlToPlay) {
        urlToPlay = await generateVoice();
      }

      // 创建或重用音频元素
      if (!audioRef.current) {
        audioRef.current = new Audio();

        // 音频事件监听
        audioRef.current.addEventListener("ended", () => {
          if (!isUnmountedRef.current) {
            setIsPlaying(false);
            onPlayStateChange?.(false);
          }
        });

        audioRef.current.addEventListener("error", () => {
          if (!isUnmountedRef.current) {
            setHasError(true);
            setIsPlaying(false);
            onPlayStateChange?.(false);
            // 只有在非组件卸载状态下才显示错误提示
            message.error("音频播放失败");
          }
        });

        audioRef.current.addEventListener("loadstart", () => {
          if (!isUnmountedRef.current) {
            setHasError(false);
          }
        });

        // 监听音频被中断的事件（页面切换、组件卸载等）
        audioRef.current.addEventListener("pause", () => {
          if (!isUnmountedRef.current) {
            setIsPlaying(false);
            onPlayStateChange?.(false);
          }
        });

        audioRef.current.addEventListener("abort", () => {
          if (!isUnmountedRef.current) {
            setIsPlaying(false);
            onPlayStateChange?.(false);
          }
        });
      }

      // 设置音频源
      if (audioRef.current.src !== urlToPlay) {
        audioRef.current.src = urlToPlay;
      }

      // 通过全局管理器播放
      globalAudioManager.play(audioRef.current, playerId);
      setIsPlaying(true);
      onPlayStateChange?.(true);
    } catch (error) {
      // 错误已经在generateVoice中处理
    }
  };

  // 停止播放
  const stopVoice = () => {
    globalAudioManager.stop(playerId);
    setIsPlaying(false);
    onPlayStateChange?.(false);
  };

  // 点击处理
  const handleClick = () => {
    if (isLoading) return;

    if (isPlaying) {
      stopVoice();
    } else {
      playVoice();
    }
  };

  // 清理资源
  useEffect(() => {
    return () => {
      // 标记组件即将卸载
      isUnmountedRef.current = true;

      if (audioRef.current) {
        // 静默停止音频，避免触发错误事件
        audioRef.current.removeEventListener("error", () => {});
        audioRef.current.removeEventListener("abort", () => {});
        audioRef.current.removeEventListener("pause", () => {});
        audioRef.current.removeEventListener("ended", () => {});
        audioRef.current.removeEventListener("loadstart", () => {});

        try {
          audioRef.current.pause();
          audioRef.current.src = "";
        } catch (e) {
          // 忽略清理过程中的错误
        }
        audioRef.current = null;
      }
      globalAudioManager.stop(playerId);
    };
  }, [playerId]);

  // 获取按钮图标
  const getIcon = () => {
    if (isLoading) {
      return <LoadingOutlined spin />;
    }
    if (hasError) {
      return <ExclamationCircleOutlined />;
    }
    if (isPlaying) {
      return <PauseOutlined />;
    }
    return <SoundOutlined />;
  };

  // 获取提示文本
  const getTooltip = () => {
    if (isLoading) {
      return "正在生成语音...";
    }
    if (hasError) {
      return "语音生成失败，点击重试";
    }
    if (isPlaying) {
      return "点击停止播放";
    }
    return audioUrl ? "点击播放语音" : "点击生成并播放语音";
  };

  return (
    <Tooltip title={getTooltip()}>
      <Button
        type="text"
        size={size}
        icon={getIcon()}
        onClick={handleClick}
        disabled={isLoading}
        style={{
          color: hasError ? "#ff4d4f" : isPlaying ? "#1890ff" : "#666",
          ...style,
        }}
      >
        {showText && (isPlaying ? "停止" : "语音")}
      </Button>
    </Tooltip>
  );
};

export default VoicePlayer;
