import type { Agent } from "../types";

interface SharedAgentsCacheEntry {
  agents: Agent[];
  updatedAt: number;
}

interface SharedAgentsRequestEntry {
  request: Promise<Agent[]>;
  updatedAt: number;
}

const sharedAgentsCache = new Map<string, SharedAgentsCacheEntry>();
const sharedAgentsRequestCache = new Map<string, SharedAgentsRequestEntry>();

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

export const setSharedAgentsCache = (
  cacheKey: string,
  agents: Agent[],
): void => {
  sharedAgentsCache.set(cacheKey, {
    agents,
    updatedAt: Date.now(),
  });
};

export const clearSharedAgentsCache = (cacheKey: string): void => {
  sharedAgentsCache.delete(cacheKey);
};

export const getSharedAgentsRequest = (
  options: GetSharedAgentsCacheOptions,
): Promise<Agent[]> | null => {
  const { cacheKey, maxAgeMs } = options;
  const requestEntry = sharedAgentsRequestCache.get(cacheKey);

  if (!requestEntry) {
    return null;
  }

  const isExpired = Date.now() - requestEntry.updatedAt > maxAgeMs;
  if (isExpired) {
    sharedAgentsRequestCache.delete(cacheKey);
    return null;
  }

  return requestEntry.request;
};

export const setSharedAgentsRequest = (
  cacheKey: string,
  request: Promise<Agent[]>,
): void => {
  sharedAgentsRequestCache.set(cacheKey, {
    request,
    updatedAt: Date.now(),
  });
};

export const clearSharedAgentsRequest = (options: {
  cacheKey: string;
  request?: Promise<Agent[]>;
}): void => {
  const { cacheKey, request } = options;
  const requestEntry = sharedAgentsRequestCache.get(cacheKey);
  if (!requestEntry) {
    return;
  }

  if (request && requestEntry.request !== request) {
    return;
  }

  sharedAgentsRequestCache.delete(cacheKey);
};

export const resetSharedAgentsCacheForTest = (): void => {
  sharedAgentsCache.clear();
  sharedAgentsRequestCache.clear();
};
