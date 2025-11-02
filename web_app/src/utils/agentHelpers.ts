/**
 * Agent 相关工具函数
 */

/**
 * 获取性别图标
 * @param gender 性别类型
 * @returns 对应的图标
 */
export const getGenderIcon = (gender: string): string => {
  switch (gender) {
    case 'MALE':
      return '♂️';
    case 'FEMALE':
      return '♀️';
    default:
      return '';
  }
};

/**
 * 获取性别文本
 * @param gender 性别类型
 * @returns 对应的文本
 */
export const getGenderText = (gender: string): string => {
  switch (gender) {
    case 'MALE':
      return '男';
    case 'FEMALE':
      return '女';
    default:
      return '未知';
  }
};

