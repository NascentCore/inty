import type { Agent } from "../types";

interface SharedAgentsCacheEntry {
  agents: Agent[];
  updatedAt: number;
}

const sharedAgentsCache = new Map<string, SharedAgentsCacheEntry>();

interface GetSharedAgentsCacheOptions {
  cacheKey: string;
  maxAgeMs: number;
}

export const getSharedAgentsCache = (
  options: GetSharedAgentsCacheOptions,
): Agent[] | null => {
  const { cacheKey, maxAgeMs } = options;
  const cacheEntry = sharedAgentsCache.get(cacheKey);

  if (!cacheEntry) {
    return null;
  }

  const isExpired = Date.now() - cacheEntry.updatedAt > maxAgeMs;
  if (isExpired) {
    sharedAgentsCache.delete(cacheKey);
    return null;
  }

  return cacheEntry.agents;
};

export const setSharedAgentsCache = (cacheKey: string, agents: Agent[]): void => {
  sharedAgentsCache.set(cacheKey, {
    agents,
    updatedAt: Date.now(),
  });
};

export const clearSharedAgentsCache = (cacheKey: string): void => {
  sharedAgentsCache.delete(cacheKey);
};

export const resetSharedAgentsCacheForTest = (): void => {
  sharedAgentsCache.clear();
};
