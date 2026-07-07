/**
 * CREATED_BY_AGENT
 */
import { describe, it, expect } from "vitest";
import type { Agent } from "../types";
import { filterAgentsByName } from "../utils/agentFilters";

const buildAgent = (name: string): Agent => ({ id: name, name }) as Agent;

describe("filterAgentsByName", () => {
  it("returns all agents when query is empty", () => {
    const agents = [buildAgent("Zara"), buildAgent("Sofia")];

    expect(filterAgentsByName(agents, " ")).toEqual(agents);
  });

  it("matches case-insensitively and by substring", () => {
    const agents = [buildAgent("Zara"), buildAgent("Sofia"), buildAgent("Nia")];

    expect(filterAgentsByName(agents, "fi")).toEqual([agents[1]]);
    expect(filterAgentsByName(agents, "ZAR")).toEqual([agents[0]]);
  });

  it("returns empty array when no match", () => {
    const agents = [buildAgent("Zara")];

    expect(filterAgentsByName(agents, "kiera")).toEqual([]);
  });
});
