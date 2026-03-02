import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Agent } from "../types";
import {
  clearSharedAgentsCache,
  getSharedAgentsCache,
  resetSharedAgentsCacheForTest,
  setSharedAgentsCache,
} from "../services/agentsSharedStore";

const buildAgents = (count: number): Agent[] =>
  Array.from({ length: count }, (_, index) => ({
    id: `agent-${index}`,
    name: `Agent ${index}`,
    visibility: "PUBLIC",
    gender: "FEMALE",
  })) as Agent[];

describe("agentsSharedStore", () => {
  beforeEach(() => {
    resetSharedAgentsCacheForTest();
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-02T00:00:00.000Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns cached agents before expiry", () => {
    const cacheKey = "agents_cache_all_admin_list_v1";
    const agents = buildAgents(2);

    setSharedAgentsCache(cacheKey, agents);

    expect(
      getSharedAgentsCache({
        cacheKey,
        maxAgeMs: 30 * 60 * 1000,
      }),
    ).toEqual(agents);
  });

  it("returns null after expiry window", () => {
    const cacheKey = "agents_cache_all_admin_list_v1";
    setSharedAgentsCache(cacheKey, buildAgents(1));

    vi.advanceTimersByTime(30 * 60 * 1000 + 1);

    expect(
      getSharedAgentsCache({
        cacheKey,
        maxAgeMs: 30 * 60 * 1000,
      }),
    ).toBeNull();
  });

  it("clears cache data by key", () => {
    const cacheKey = "agents_cache_all_admin_list_v1";
    setSharedAgentsCache(cacheKey, buildAgents(3));

    clearSharedAgentsCache(cacheKey);

    expect(
      getSharedAgentsCache({
        cacheKey,
        maxAgeMs: 30 * 60 * 1000,
      }),
    ).toBeNull();
  });
});
