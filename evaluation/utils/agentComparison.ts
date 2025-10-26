import { isEqual } from "lodash";
import type { Agent } from "inty_sdk/src/resources/api/v1/ai/agents";

/**
 * 深度比较两个智能体对象，检测是否有变化
 * 使用Lodash的isEqual方法进行精确的深度比较
 * @param origin 原始智能体对象
 * @param copy 复制的智能体对象
 * @returns 如果有变化返回 true，否则返回 false
 */
export const hasAgentChanged = (
  original: Agent | null,
  copy: Agent | null,
): boolean => {
  if (!original || !copy) return false;

  try {
// 使用 Lodash 的 isEqual 进行深度比较
// isEqual 会自动处理 undefined、null、请求对象等复杂情况
    return !isEqual(original, copy);
  } catch (error) {
    console.warn("Lodash isEqual comparison failed:", error);
// 如果 isEqual 失败，使用简单的 JSON 字符串比较作为回退
    try {
      return JSON.stringify(original) !== JSON.stringify(copy);
    } catch {
      return true; // 如果所有比较都失败，认为有变化
    }
  }
};

/**
 *获取智能体对象之间的两个具体差异
 * 使用Lodash的方法来获取差异信息
 * @param origin 原始智能体对象
 * @param copy 复制的智能体对象
 * @returns 差异对象，如果没有差异则返回 undefined
 */
export const getAgentDifferences = (
  original: Agent | null,
  copy: Agent | null,
) => {
  if (!original || !copy) return undefined;

  try {
// 使用 Lodash 的 isEqual 检查是否有差异
    if (isEqual(original, copy)) {
      return undefined; // 没有差异
    }
// 如果存在差异，则返回一个简化的差异信息
// 注意：Lodash 的 isEqual 只返回布尔值，不提供具体差异
// 这里我们返回一个指示有差异的对象
    return {
      hasChanges: true,
      message:
        "Objects are different (detailed diff not available with isEqual)",
    };
  } catch (error) {
    console.warn("Lodash comparison failed in getAgentDifferences:", error);
    return undefined; // 如果比较失败，返回 undefined
  }
};
