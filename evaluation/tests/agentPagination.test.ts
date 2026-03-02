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
    const pageSize = AGENT_LIST_PAGE_SIZE;
    const fetchPage = vi
      .fn()
      .mockResolvedValueOnce(buildAgents(pageSize, 0))
      .mockResolvedValueOnce(buildAgents(pageSize, pageSize))
      .mockResolvedValueOnce(buildAgents(5, pageSize * 2));
    const onBatchLoaded = vi.fn();

    const result = await fetchAllAgentsWithPagination({
      fetchPage,
      pageSize,
      onBatchLoaded,
    });

    expect(result).toHaveLength(pageSize * 2 + 5);
    expect(fetchPage).toHaveBeenCalledTimes(3);
    expect(fetchPage).toHaveBeenNthCalledWith(1, { skip: 0, limit: pageSize });
    expect(fetchPage).toHaveBeenNthCalledWith(2, {
      skip: pageSize,
      limit: pageSize,
    });
    expect(fetchPage).toHaveBeenNthCalledWith(3, {
      skip: pageSize * 2,
      limit: pageSize,
    });

    expect(onBatchLoaded).toHaveBeenCalledTimes(3);
    expect(onBatchLoaded.mock.calls[0][0]).toHaveLength(pageSize);
    expect(onBatchLoaded.mock.calls[1][0]).toHaveLength(pageSize * 2);
    expect(onBatchLoaded.mock.calls[2][0]).toHaveLength(pageSize * 2 + 5);
  });

  it("supports early stop through shouldContinue", async () => {
    const pageSize = AGENT_LIST_PAGE_SIZE;
    let keepLoading = true;
    const fetchPage = vi
      .fn()
      .mockResolvedValueOnce(buildAgents(pageSize, 0))
      .mockResolvedValueOnce(buildAgents(pageSize, pageSize));

    const result = await fetchAllAgentsWithPagination({
      fetchPage,
      pageSize,
      onBatchLoaded: () => {
        keepLoading = false;
      },
      shouldContinue: () => keepLoading,
    });

    expect(result).toHaveLength(pageSize);
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
    expect(fetchPage).toHaveBeenCalledWith({
      skip: 0,
      limit: AGENT_LIST_PAGE_SIZE,
    });
  });
});
