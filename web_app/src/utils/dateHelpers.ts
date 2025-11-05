/**
 * 日期时间相关工具函数
 */

/**
 * 格式化消息时间
 * 智能显示：刚刚、N分钟前、HH:MM、MM-DD HH:MM
 * @param timestamp 时间戳
 * @returns 格式化后的时间字符串
 */
export const formatMessageTime = (timestamp: string): string => {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    // 一分钟内
    if (diff < 60000) {
      return '刚刚';
    }

    // 一小时内
    if (diff < 3600000) {
      return `${Math.floor(diff / 60000)} 分钟前`;
    }

    // 今天
    if (date.toDateString() === now.toDateString()) {
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      });
    }

    // 其他日期
    return date.toLocaleDateString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
};

/**
 * 格式化日期为标准格式
 * @param timestamp 时间戳
 * @returns YYYY-MM-DD HH:MM:SS
 */
export const formatDateTime = (timestamp: string): string => {
  try {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return '';
  }
};
