import type { Agent } from "../types";

export const AGENT_LIST_PAGE_SIZE = 50;

export interface FetchAllAgentsWithPaginationOptions {
  fetchPage: (params: { skip: number; limit: number }) => Promise<Agent[]>;
  pageSize?: number;
  onBatchLoaded?: (accumulatedAgents: Agent[], batchAgents: Agent[]) => void;
  shouldContinue?: () => boolean;
}

const yieldToMainThread = async () => {
  await new Promise<void>((resolve) => {
    setTimeout(resolve, 0);
  });
};

export const fetchAllAgentsWithPagination = async (
  options: FetchAllAgentsWithPaginationOptions,
): Promise<Agent[]> => {
  const { fetchPage, onBatchLoaded, shouldContinue } = options;
  const pageSize = Math.max(1, options.pageSize ?? AGENT_LIST_PAGE_SIZE);
  const allAgents: Agent[] = [];
  let skip = 0;
  let hasNextPage = true;

  while (hasNextPage) {
    if (shouldContinue && !shouldContinue()) {
      hasNextPage = false;
      continue;
    }

    const pageAgents = await fetchPage({ skip, limit: pageSize });
    const normalizedPageAgents = Array.isArray(pageAgents) ? pageAgents : [];

    if (normalizedPageAgents.length === 0) {
      hasNextPage = false;
      continue;
    }

    allAgents.push(...normalizedPageAgents);
    onBatchLoaded?.([...allAgents], normalizedPageAgents);

    if (normalizedPageAgents.length < pageSize) {
      hasNextPage = false;
      continue;
    }

    skip += pageSize;
    await yieldToMainThread();
  }

  return allAgents;
};
