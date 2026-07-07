/**
 * 音色预览播放组件
 * 用于播放音色的 preview_url 预览音频
 */

import React, { useState, useRef, useEffect } from "react";
import { Button, Tooltip, message } from "antd";
import {
  PlayCircleOutlined,
  PauseOutlined,
  LoadingOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";

interface VoicePreviewPlayerProps {
  // 预览音频URL
  previewUrl?: string;
  // 音色名称（用于提示）
  voiceName?: string;
  // 样式控制
  size?: "small" | "middle" | "large";
  // 是否显示文字
  showText?: boolean;
  // 自定义样式
  style?: React.CSSProperties;
  // 播放状态变化回调
  onPlayStateChange?: (isPlaying: boolean) => void;
}

// 全局音频管理器 - 确保同时只有一个预览音频在播放
class GlobalPreviewAudioManager {
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

const globalPreviewAudioManager = new GlobalPreviewAudioManager();

export const VoicePreviewPlayer: React.FC<VoicePreviewPlayerProps> = ({
  previewUrl,
  voiceName = "音色",
  size = "small",
  showText = false,
  style,
  onPlayStateChange,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasError, setHasError] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const playerId = useRef(`preview-${Date.now()}-${Math.random()}`).current;
  const isUnmountedRef = useRef(false);

  // 注册全局音频管理器监听
  useEffect(() => {
    const handleGlobalPlayStateChange = (playing: boolean) => {
      if (!playing && isPlaying) {
        setIsPlaying(false);
        onPlayStateChange?.(false);
      }
    };

    globalPreviewAudioManager.registerListener(
      playerId,
      handleGlobalPlayStateChange,
    );

    return () => {
      globalPreviewAudioManager.unregisterListener(playerId);
    };
  }, [playerId, isPlaying, onPlayStateChange]);

  // 播放预览音频
  const playPreview = async () => {
    if (!previewUrl) {
      message.warning("该音色暂无预览音频");
      return;
    }

    try {
      setIsLoading(true);
      setHasError(false);

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
            message.error("预览音频播放失败");
          }
        });

        audioRef.current.addEventListener("loadstart", () => {
          if (!isUnmountedRef.current) {
            setHasError(false);
          }
        });

        // 监听音频被中断的事件
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
      if (audioRef.current.src !== previewUrl) {
        audioRef.current.src = previewUrl;
      }

      // 通过全局管理器播放
      globalPreviewAudioManager.play(audioRef.current, playerId);
      setIsPlaying(true);
      onPlayStateChange?.(true);
    } catch (error) {
      console.error("预览音频播放失败:", error);
      setHasError(true);
      message.error("预览音频播放失败");
    } finally {
      setIsLoading(false);
    }
  };

  // 停止播放
  const stopPreview = () => {
    globalPreviewAudioManager.stop(playerId);
    setIsPlaying(false);
    onPlayStateChange?.(false);
  };

  // 点击处理
  const handleClick = () => {
    if (isLoading || !previewUrl) return;

    if (isPlaying) {
      stopPreview();
    } else {
      playPreview();
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
      globalPreviewAudioManager.stop(playerId);
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
    return <PlayCircleOutlined />;
  };

  // 获取提示文本
  const getTooltip = () => {
    if (!previewUrl) {
      return "该音色暂无预览音频";
    }
    if (isLoading) {
      return "正在加载预览音频...";
    }
    if (hasError) {
      return "预览音频播放失败，点击重试";
    }
    if (isPlaying) {
      return `正在播放 ${voiceName} 预览音频，点击停止`;
    }
    return `点击播放 ${voiceName} 预览音频`;
  };

  return (
    <Tooltip title={getTooltip()}>
      <Button
        type="text"
        size={size}
        icon={getIcon()}
        onClick={handleClick}
        disabled={isLoading || !previewUrl}
        style={{
          color: hasError
            ? "#ff4d4f"
            : isPlaying
              ? "#1890ff"
              : previewUrl
                ? "#52c41a"
                : "#d9d9d9",
          border: "none",
          boxShadow: "none",
          ...style,
        }}
      >
        {showText && (isPlaying ? "停止" : "预览")}
      </Button>
    </Tooltip>
  );
};

export default VoicePreviewPlayer;
