import type { Agent } from "../types";

export const getGeneratedImageCount = (
  agentId: string,
  imageCounts: Record<string, number>,
): number => imageCounts[agentId] ?? 0;

export const rankAgentsByGeneratedImageCount = (
  agents: Agent[],
  imageCounts: Record<string, number>,
): Agent[] =>
  [...agents].sort((left, right) => {
    const countDelta =
      getGeneratedImageCount(right.id, imageCounts) -
      getGeneratedImageCount(left.id, imageCounts);
    if (countDelta !== 0) {
      return countDelta;
    }

    const nameDelta = left.name.localeCompare(right.name);
    if (nameDelta !== 0) {
      return nameDelta;
    }

    return left.id.localeCompare(right.id);
  });
