import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Agent } from "../types";
import {
  clearSharedAgentsCache,
  clearSharedAgentsRequest,
  getSharedAgentsCache,
  getSharedAgentsRequest,
  resetSharedAgentsCacheForTest,
  setSharedAgentsCache,
  setSharedAgentsRequest,
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

  it("returns shared loading request before expiry", () => {
    const cacheKey = "agents_cache_all_admin_list_v1";
    const loadingRequest = Promise.resolve(buildAgents(2));
    setSharedAgentsRequest(cacheKey, loadingRequest);

    expect(
      getSharedAgentsRequest({
        cacheKey,
        maxAgeMs: 30 * 60 * 1000,
      }),
    ).toBe(loadingRequest);
  });

  it("removes expired shared loading request", () => {
    const cacheKey = "agents_cache_all_admin_list_v1";
    const loadingRequest = Promise.resolve(buildAgents(1));
    setSharedAgentsRequest(cacheKey, loadingRequest);

    vi.advanceTimersByTime(30 * 60 * 1000 + 1);

    expect(
      getSharedAgentsRequest({
        cacheKey,
        maxAgeMs: 30 * 60 * 1000,
      }),
    ).toBeNull();
  });

  it("clears shared loading request only when request matches", () => {
    const cacheKey = "agents_cache_all_admin_list_v1";
    const activeRequest = Promise.resolve(buildAgents(2));
    const staleRequest = Promise.resolve(buildAgents(1));
    setSharedAgentsRequest(cacheKey, activeRequest);

    clearSharedAgentsRequest({
      cacheKey,
      request: staleRequest,
    });

    expect(
      getSharedAgentsRequest({
        cacheKey,
        maxAgeMs: 30 * 60 * 1000,
      }),
    ).toBe(activeRequest);

    clearSharedAgentsRequest({
      cacheKey,
      request: activeRequest,
    });

    expect(
      getSharedAgentsRequest({
        cacheKey,
        maxAgeMs: 30 * 60 * 1000,
      }),
    ).toBeNull();
  });
});
