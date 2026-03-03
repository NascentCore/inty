import { describe, expect, it } from "vitest";
import type { Agent } from "../types";
import {
  filterAgentsForSingleSelector,
  shouldShowSingleSelectorEmptySearch,
} from "../utils/singleAgentSelector";

const buildAgent = (id: string, name: string): Agent =>
  ({
    id,
    name,
    visibility: "PUBLIC",
    gender: "MALE",
  }) as Agent;

describe("singleAgentSelector utils", () => {
  it("returns all agents when query is empty", () => {
    const agents = [buildAgent("1", "Henry"), buildAgent("2", "Mateo")];
    expect(filterAgentsForSingleSelector(agents, " ")).toEqual(agents);
  });

  it("filters by agent name case-insensitively", () => {
    const agents = [buildAgent("1", "Henry"), buildAgent("2", "Jace")];
    expect(filterAgentsForSingleSelector(agents, "he")).toEqual([agents[0]]);
    expect(filterAgentsForSingleSelector(agents, "JAC")).toEqual([agents[1]]);
  });

  it("shows search empty state only when query exists and no match", () => {
    expect(shouldShowSingleSelectorEmptySearch(3, "abc", 0)).toBe(true);
    expect(shouldShowSingleSelectorEmptySearch(3, " ", 0)).toBe(false);
    expect(shouldShowSingleSelectorEmptySearch(0, "abc", 0)).toBe(false);
    expect(shouldShowSingleSelectorEmptySearch(3, "abc", 1)).toBe(false);
  });
});

