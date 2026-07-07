import type { SessionMessagesResponse } from "../types";

type SessionMessagesPaginationData = Pick<
  SessionMessagesResponse,
  "total" | "size" | "page" | "has_more"
>;

/**
 * 会话消息分页的展示规则：
 * - 有下一页时显示；
 * - 已经翻到第 2 页及之后时继续显示（便于回跳）；
 * - 总条数超过单页容量时显示（支持直接跳页）。
 */
export const shouldShowSessionMessagesPagination = (
  data: SessionMessagesPaginationData,
): boolean => {
  return data.has_more || data.page > 1 || data.total > data.size;
};

export const sessionMessagesPaginationProps = {
  showSizeChanger: false,
  showQuickJumper: true,
  showLessItems: true,
} as const;
