/**
 * MessageItem 组件
 * 单条聊天消息展示
 */

import { Bot, Loader2, User, Volume2, VolumeX } from 'lucide-react';
import React from 'react';
import { Icon } from '@/components';
import { useVoicePlayer } from '@/hooks';
import type { IMessage } from '@/types';
import { formatMessageTime } from '@/utils';
import './index.less';

/**
 * MessageItem 组件 Props
 */
interface IMessageItemProps {
  /** 消息数据 */
  message: IMessage;
  /** 是否显示头像 */
  showAvatar?: boolean;
  /** AI Agent 头像 URL（用于显示 assistant 的真实头像） */
  agentAvatar?: string | null;
  /** Agent ID（用于生成语音） */
  agentId?: string;
}

/**
 * MessageItem 组件
 */
const MessageItem: React.FC<IMessageItemProps> = ({
  message,
  showAvatar = true,
  agentAvatar,
  agentId,
}) => {
  const isUser = message.role === 'user';

  // 使用语音播放 Hook
  const { voiceStatus, playVoice, stopVoice } = useVoicePlayer({
    agentId,
    messageId: message.id,
    audioUrl: message.audio_url, // 优先使用消息体中的音频 URL
  });

  return (
    <div className={`message-item ${isUser ? 'message-user' : 'message-assistant'}`}>
      {/* 头像 */}
      {showAvatar && (
        <div className="message-avatar">
          {isUser ? (
            <div className="avatar-user">
              <Icon icon={User} size={20} />
            </div>
          ) : agentAvatar ? (
            <div className="avatar-assistant" style={{ backgroundImage: `url(${agentAvatar})` }} />
          ) : (
            <div className="avatar-assistant">
              <Icon icon={Bot} size={20} />
            </div>
          )}
        </div>
      )}

      {/* 消息内容区 */}
      <div className="message-content-wrapper">
        {/* 消息气泡 */}
        <div className="message-bubble">
          <div className="message-text">{message.content}</div>
        </div>

        {/* 底部信息栏：时间戳 + 语音按钮 */}
        <div className="message-footer">
          {/* 时间戳 */}
          <div className="message-time">{formatMessageTime(message.timestamp)}</div>

          {/* 语音播放按钮（仅对 AI 消息显示） */}
          {!isUser && agentId && (
            <button
              type="button"
              className={`voice-button voice-button-${voiceStatus}`}
              onClick={voiceStatus === 'playing' ? stopVoice : playVoice}
              disabled={voiceStatus === 'loading'}
              title={voiceStatus === 'playing' ? 'Stop playback' : 'Play voice'}
            >
              {voiceStatus === 'loading' && <Icon icon={Loader2} size={14} />}
              {voiceStatus === 'playing' && <Icon icon={VolumeX} size={14} />}
              {voiceStatus === 'idle' && <Icon icon={Volume2} size={14} />}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageItem;
