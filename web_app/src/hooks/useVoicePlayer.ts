/**
 * useVoicePlayer Hook
 * 封装语音播放逻辑
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { createIntyClient, logger } from '@/utils';

/**
 * 语音播放状态类型
 */
export type TVoiceStatus = 'idle' | 'loading' | 'playing';

/**
 * useVoicePlayer Hook 参数
 */
interface IUseVoicePlayerParams {
  /** Agent ID */
  agentId?: string;
  /** Message ID */
  messageId: string | number;
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
 *   messageId: 'msg_456'
 * });
 * ```
 * 
 * 功能特性：
 * - 自动缓存音频 URL，避免重复请求
 * - 支持播放/停止控制
 * - 自动资源清理
 * - 错误处理和日志记录
 */
export const useVoicePlayer = ({
  agentId,
  messageId,
}: IUseVoicePlayerParams): IUseVoicePlayerReturn => {
  // 语音播放状态
  const [voiceStatus, setVoiceStatus] = useState<TVoiceStatus>('idle');
  
  // 音频 URL 缓存
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  
  // 音频播放器引用
  const audioRef = useRef<HTMLAudioElement | null>(null);

  /**
   * 播放语音
   */
  const playVoice = useCallback(async () => {
    if (!agentId || !messageId) {
      logger.warn('缺少 agentId 或 messageId，无法生成语音');
      return;
    }

    try {
      // 如果已有音频 URL，直接播放
      if (audioUrl && audioRef.current) {
        setVoiceStatus('playing');
        await audioRef.current.play();
        return;
      }

      // 生成语音
      setVoiceStatus('loading');
      const client = await createIntyClient(true);
      
      const response = await client.api.v1.chats.agents.generateMessageVoice(
        String(messageId),
        { agent_id: agentId },
      );

      // 从响应中提取 audio_url
      let url: string | null = null;
      
      if (response && typeof response === 'object' && 'data' in response) {
        // 响应格式：{ code, message, data: { audio_url } }
        const data = (response as any).data;
        if (data && typeof data === 'object' && 'audio_url' in data) {
          url = data.audio_url;
        }
      }

      if (!url) {
        throw new Error('无法从响应中获取音频 URL');
      }

      setAudioUrl(url);

      // 创建并播放音频
      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onplay = () => setVoiceStatus('playing');
      audio.onended = () => setVoiceStatus('idle');
      audio.onerror = () => {
        logger.error('音频播放失败');
        setVoiceStatus('idle');
      };

      await audio.play();
    } catch (err) {
      logger.error('生成语音失败:', err);
      setVoiceStatus('idle');
    }
  }, [agentId, messageId, audioUrl]);

  /**
   * 停止播放语音
   */
  const stopVoice = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setVoiceStatus('idle');
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

