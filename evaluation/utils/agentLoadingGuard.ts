export interface AgentLoadingGuardInput {
  hasLoaded: boolean;
  isLoading: boolean;
  agentsCount: number;
}

/**
 * 关键步骤总结：
 * - 区分“未加载过”与“已加载但为空”，避免页面切换时重复请求
 * - 仅在首次进入且无数据、也不在加载中时触发自动加载
 */
export const shouldLoadAgentsOnPageEnter = (
  input: AgentLoadingGuardInput,
): boolean => {
  return !input.hasLoaded && !input.isLoading && input.agentsCount === 0;
};
