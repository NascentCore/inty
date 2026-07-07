import { describe, expect, it } from "vitest";
import type { Agent } from "../types";
import {
  getGeneratedImageCount,
  rankAgentsByGeneratedImageCount,
} from "../utils/generatedImagesRanking";

const buildAgent = (id: string, name: string): Agent =>
  ({
    id,
    name,
    visibility: "PUBLIC",
  }) as Agent;

describe("generatedImagesRanking", () => {
  it("ranks agents by generated image counts in descending order", () => {
    const agents = [
      buildAgent("agent-a", "Ada"),
      buildAgent("agent-b", "Callie"),
      buildAgent("agent-c", "Violet"),
    ];
    const imageCounts = {
      "agent-a": 2,
      "agent-b": 8,
      "agent-c": 5,
    };

    const rankedAgents = rankAgentsByGeneratedImageCount(agents, imageCounts);

    expect(rankedAgents.map((agent) => agent.id)).toEqual([
      "agent-b",
      "agent-c",
      "agent-a",
    ]);
  });

  it("treats missing counts as zero and uses deterministic tie breakers", () => {
    const agents = [
      buildAgent("agent-z", "Zoe"),
      buildAgent("agent-a", "Ada"),
      buildAgent("agent-b", "Bea"),
    ];
    const imageCounts = {
      "agent-b": 1,
    };

    const rankedAgents = rankAgentsByGeneratedImageCount(agents, imageCounts);

    expect(rankedAgents.map((agent) => agent.id)).toEqual([
      "agent-b",
      "agent-a",
      "agent-z",
    ]);
    expect(getGeneratedImageCount("unknown-agent", imageCounts)).toBe(0);
  });

  it("does not mutate the input agent array", () => {
    const agents = [buildAgent("agent-a", "Ada"), buildAgent("agent-b", "Bea")];
    const originalOrder = agents.map((agent) => agent.id);

    rankAgentsByGeneratedImageCount(agents, { "agent-b": 3 });

    expect(agents.map((agent) => agent.id)).toEqual(originalOrder);
  });
});
