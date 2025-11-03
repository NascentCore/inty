/**
 * useVoicePlayer Hook
 * 封装语音播放逻辑
 */

import { generateMessageVoice, VoiceGenerationError } from "@/services/chat";
import { logger } from "@/utils";
import { useModel } from "@umijs/max";
import { useCallback, useEffect, useRef, useState } from "react";

/**
 * 语音播放状态类型
 */
export type TVoiceStatus = "idle" | "loading" | "playing";

/**
 * useVoicePlayer Hook 参数
 */
interface IUseVoicePlayerParams {
  /** Agent ID */
  agentId?: string;
  /** Message ID */
  messageId: string | number;
  /** 已有的音频 URL（如果有则直接使用，无需调用 API） */
  audioUrl?: string | null;
}

/**
 * useVoicePlayer Hook 返回值
 */
interface IUseVoicePlayerReturn {
  /** 当前播放状态 */
  voiceStatus: TVoiceStatus;
  /** 播放语音 */
  playVoice: () => Promise<void>;
  /** 停止播放 */
  stopVoice: () => void;
}

/**
 * 语音播放 Hook
 *
 * 用途：管理消息语音的生成和播放
 * 使用示例：
 * ```tsx
 * const { voiceStatus, playVoice, stopVoice } = useVoicePlayer({
 *   agentId: 'agent_123',
 *   messageId: 'msg_456',
 *   audioUrl: message.audio_url // 可选，如果有则直接使用
 * });
 * ```
 *
 * 功能特性：
 * - 优先使用已有音频 URL，避免重复请求
 * - 自动缓存音频 URL
 * - 支持播放/停止控制
 * - 自动资源清理
 * - 错误处理和日志记录
 */
export const useVoicePlayer = ({
  agentId,
  messageId,
  audioUrl: propsAudioUrl,
}: IUseVoicePlayerParams): IUseVoicePlayerReturn => {
  // 获取 Google 登录弹窗状态管理
  const googleLoginModal = useModel("googleLoginModal");

  // 语音播放状态
  const [voiceStatus, setVoiceStatus] = useState<TVoiceStatus>("idle");

  // 音频 URL 缓存（来自 API 生成）
  const [cachedAudioUrl, setCachedAudioUrl] = useState<string | null>(null);

  // 音频播放器引用
  const audioRef = useRef<HTMLAudioElement | null>(null);

  /**
   * 播放语音
   */
  const playVoice = useCallback(async () => {
    try {
      // 优先使用 props 传入的 audioUrl，其次使用缓存的 URL
      const audioUrlToUse = propsAudioUrl || cachedAudioUrl;

      // 如果已有音频 URL，直接播放
      if (audioUrlToUse) {
        // 如果已有播放器且 URL 相同，直接播放
        if (audioRef.current && audioRef.current.src === audioUrlToUse) {
          setVoiceStatus("playing");
          await audioRef.current.play();
          return;
        }

        // 创建新的播放器
        const audio = new Audio(audioUrlToUse);
        audioRef.current = audio;

        audio.onplay = () => setVoiceStatus("playing");
        audio.onended = () => setVoiceStatus("idle");
        audio.onerror = () => {
          logger.error("音频播放失败");
          setVoiceStatus("idle");
        };

        setVoiceStatus("playing");
        await audio.play();
        return;
      }

      // 如果没有音频 URL，需要调用 API 生成
      if (!agentId || !messageId) {
        logger.warn("缺少 agentId 或 messageId，无法生成语音");
        return;
      }

      // 生成语音
      setVoiceStatus("loading");
      const voiceData = await generateMessageVoice(messageId, agentId);

      // 缓存音频 URL
      setCachedAudioUrl(voiceData.audio_url);

      // 创建并播放音频
      const audio = new Audio(voiceData.audio_url);
      audioRef.current = audio;

      audio.onplay = () => setVoiceStatus("playing");
      audio.onended = () => setVoiceStatus("idle");
      audio.onerror = () => {
        logger.error("音频播放失败");
        setVoiceStatus("idle");
      };

      await audio.play();
    } catch (err) {
      logger.error("播放语音失败:", err);
      setVoiceStatus("idle");

      // 处理 GUEST_LOGIN_REQUIRED 错误
      if (err instanceof VoiceGenerationError && err.shouldLogin) {
        logger.info("需要 Google 登录，打开登录弹窗");
        googleLoginModal.show();
      }
    }
  }, [agentId, messageId, propsAudioUrl, cachedAudioUrl, googleLoginModal]);

  /**
   * 停止播放语音
   */
  const stopVoice = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setVoiceStatus("idle");
    }
  }, []);

  /**
   * 组件卸载时清理音频资源
   */
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  return {
    voiceStatus,
    playVoice,
    stopVoice,
  };
};
