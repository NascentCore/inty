/**
 * 侧边栏相关工具函数
 */

import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

// 配置 dayjs
dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

/**
 * 格式化最后消息时间
 * @param time - ISO 时间字符串
 * @returns 相对时间字符串（如 "3 小时前"）
 */
export const formatLastMessageTime = (time: string): string => {
  return dayjs(time).fromNow();
};

/**
 * 截断消息内容
 * @param message - 原始消息内容
 * @param maxLength - 最大长度，默认 40
 * @returns 截断后的消息内容
 */
export const truncateMessage = (message: string, maxLength: number = 40): string => {
  if (!message) return '暂无消息';
  if (message.length <= maxLength) return message;
  return `${message.substring(0, maxLength)}...`;
};

/**
 * 判断聊天项是否为当前活跃会话
 * @param agentId - Agent ID
 * @param pathname - 当前路径
 * @returns 是否为活跃会话
 */
export const isChatActive = (agentId: string, pathname: string): boolean => {
  // 匹配 /chat/:agentId 路径
  const chatPathRegex = /^\/chat\/(.+)$/;
  const match = pathname.match(chatPathRegex);

  if (match?.[1]) {
    const currentAgentId = match[1];
    return agentId === currentAgentId;
  }

  return false;
};
