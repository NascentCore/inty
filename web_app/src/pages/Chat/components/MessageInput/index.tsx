/**
 * MessageInput 组件
 * 聊天消息输入框
 */

import { Send } from 'lucide-react';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Icon } from '@/components';
import './index.less';

/**
 * MessageInput 组件 Props
 */
interface IMessageInputProps {
  /** 发送消息回调 */
  onSend: (content: string) => void;
  /** 是否正在发送 */
  sending?: boolean;
  /** 是否禁用 */
  disabled?: boolean;
  /** 占位符文本 */
  placeholder?: string;
}

/**
 * MessageInput 组件
 */
const MessageInput: React.FC<IMessageInputProps> = ({
  onSend,
  sending = false,
  disabled = false,
  placeholder = 'Type a message...',
}) => {
  const [inputValue, setInputValue] = useState<string>('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /**
   * 处理输入变化
   */
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
  }, []);

  /**
   * 自动调整输入框高度
   */
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      // 重置高度以正确计算 scrollHeight
      textarea.style.height = 'auto';
      // 设置新高度，限制最大高度
      const newHeight = Math.min(textarea.scrollHeight, 200);
      textarea.style.height = `${newHeight}px`;
    }
  }, [inputValue]);

  /**
   * 处理发送
   */
  const handleSend = useCallback(() => {
    const trimmedValue = inputValue.trim();
    if (!trimmedValue || sending || disabled) {
      return;
    }

    onSend(trimmedValue);
    setInputValue('');

    // 重置输入框高度
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [inputValue, onSend, sending, disabled]);

  /**
   * 处理键盘事件
   */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Enter 发送，Shift+Enter 换行
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  /**
   * 判断是否可以发送
   */
  const canSend = inputValue.trim().length > 0 && !sending && !disabled;

  return (
    <div className="message-input-container">
      <div className="message-input-wrapper">
        {/* 输入框 */}
        <textarea
          ref={textareaRef}
          className="message-input"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || sending}
          rows={1}
        />

        {/* 发送按钮 */}
        <button
          className={`send-button ${canSend ? 'active' : ''} ${sending ? 'sending' : ''}`}
          onClick={handleSend}
          disabled={!canSend || sending}
          type="button"
        >
          {sending ? (
            <span className="sending-spinner">
              <div className="bounce1" />
              <div className="bounce2" />
              <div className="bounce3" />
            </span>
          ) : (
            <span className="send-icon">
              <Icon icon={Send} size={20} />
            </span>
          )}
        </button>
      </div>

      {/* 提示文本 */}
      <div className="message-input-hint">Press Enter to send, Shift + Enter for new line</div>
    </div>
  );
};

export default MessageInput;
