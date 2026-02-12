import { describe, it, expect, vi } from "vitest";
import type { Agent } from "../types";
import {
  AGENT_LIST_PAGE_SIZE,
  fetchAllAgentsWithPagination,
} from "../utils/agentPagination";

const buildAgents = (count: number, startIndex = 0): Agent[] =>
  Array.from({ length: count }, (_, index) => ({
    id: `agent-${startIndex + index}`,
    name: `Agent ${startIndex + index}`,
  })) as Agent[];

describe("fetchAllAgentsWithPagination", () => {
  it("loads agents by pages and emits incremental batches", async () => {
    const fetchPage = vi
      .fn()
      .mockResolvedValueOnce(buildAgents(20, 0))
      .mockResolvedValueOnce(buildAgents(20, 20))
      .mockResolvedValueOnce(buildAgents(5, 40));
    const onBatchLoaded = vi.fn();

    const result = await fetchAllAgentsWithPagination({
      fetchPage,
      pageSize: AGENT_LIST_PAGE_SIZE,
      onBatchLoaded,
    });

    expect(result).toHaveLength(45);
    expect(fetchPage).toHaveBeenCalledTimes(3);
    expect(fetchPage).toHaveBeenNthCalledWith(1, { skip: 0, limit: 20 });
    expect(fetchPage).toHaveBeenNthCalledWith(2, { skip: 20, limit: 20 });
    expect(fetchPage).toHaveBeenNthCalledWith(3, { skip: 40, limit: 20 });

    expect(onBatchLoaded).toHaveBeenCalledTimes(3);
    expect(onBatchLoaded.mock.calls[0][0]).toHaveLength(20);
    expect(onBatchLoaded.mock.calls[1][0]).toHaveLength(40);
    expect(onBatchLoaded.mock.calls[2][0]).toHaveLength(45);
  });

  it("supports early stop through shouldContinue", async () => {
    let keepLoading = true;
    const fetchPage = vi
      .fn()
      .mockResolvedValueOnce(buildAgents(20, 0))
      .mockResolvedValueOnce(buildAgents(20, 20));

    const result = await fetchAllAgentsWithPagination({
      fetchPage,
      pageSize: AGENT_LIST_PAGE_SIZE,
      onBatchLoaded: () => {
        keepLoading = false;
      },
      shouldContinue: () => keepLoading,
    });

    expect(result).toHaveLength(20);
    expect(fetchPage).toHaveBeenCalledTimes(1);
  });

  it("returns empty list when first page has no data", async () => {
    const fetchPage = vi.fn().mockResolvedValueOnce([]);
    const onBatchLoaded = vi.fn();

    const result = await fetchAllAgentsWithPagination({
      fetchPage,
      pageSize: AGENT_LIST_PAGE_SIZE,
      onBatchLoaded,
    });

    expect(result).toEqual([]);
    expect(onBatchLoaded).not.toHaveBeenCalled();
    expect(fetchPage).toHaveBeenCalledWith({ skip: 0, limit: 20 });
  });
});
