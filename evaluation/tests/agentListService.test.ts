import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Agent } from "../types";
import { agentApi } from "../services/api";
import {
  filterAgentsByType,
  loadAdminAgentList,
  loadSelfAgentList,
} from "../services/agentListService";
import { AGENT_LIST_PAGE_SIZE } from "../utils/agentPagination";

vi.mock("../services/api", () => ({
  agentApi: {
    listAll: vi.fn(),
    list: vi.fn(),
  },
}));

const buildAgents = (
  count: number,
  startIndex = 0,
  visibility: "PUBLIC" | "PRIVATE" = "PUBLIC",
): Agent[] =>
  Array.from({ length: count }, (_, index) => ({
    id: `agent-${startIndex + index}`,
    name: `Agent ${startIndex + index}`,
    visibility,
  })) as Agent[];

describe("agentListService", () => {
  beforeEach(() => {
    vi.mocked(agentApi.listAll).mockReset();
    vi.mocked(agentApi.list).mockReset();
  });

  it("loads admin agents with paginated strategy", async () => {
    vi.mocked(agentApi.listAll)
      .mockResolvedValueOnce(buildAgents(AGENT_LIST_PAGE_SIZE, 0, "PUBLIC"))
      .mockResolvedValueOnce(buildAgents(3, AGENT_LIST_PAGE_SIZE, "PRIVATE"));

    const onBatchLoaded = vi.fn();
    const agents = await loadAdminAgentList({ onBatchLoaded });

    expect(agents).toHaveLength(AGENT_LIST_PAGE_SIZE + 3);
    expect(vi.mocked(agentApi.listAll)).toHaveBeenCalledTimes(2);
    expect(vi.mocked(agentApi.listAll)).toHaveBeenNthCalledWith(1, {
      skip: 0,
      limit: AGENT_LIST_PAGE_SIZE,
    });
    expect(vi.mocked(agentApi.listAll)).toHaveBeenNthCalledWith(2, {
      skip: AGENT_LIST_PAGE_SIZE,
      limit: AGENT_LIST_PAGE_SIZE,
    });
    expect(onBatchLoaded).toHaveBeenCalledTimes(2);
  });

  it("loads self agents and maps type filter to API params", async () => {
    vi.mocked(agentApi.list).mockResolvedValueOnce(buildAgents(5, 0, "PUBLIC"));

    const agents = await loadSelfAgentList({ type: "public" });

    expect(agents).toHaveLength(5);
    expect(vi.mocked(agentApi.list)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(agentApi.list)).toHaveBeenCalledWith({
      type: "public",
      skip: 0,
      limit: AGENT_LIST_PAGE_SIZE,
    });
  });

  it("filters agent list by visibility type", () => {
    const allAgents = [
      ...buildAgents(2, 0, "PUBLIC"),
      ...buildAgents(3, 2, "PRIVATE"),
    ];

    expect(filterAgentsByType(allAgents, "all")).toHaveLength(5);
    expect(filterAgentsByType(allAgents, "public")).toHaveLength(2);
    expect(filterAgentsByType(allAgents, "private")).toHaveLength(3);
  });
});
