import type { Agent } from "../types";

const normalizeSearchText = (value: string): string =>
  value.trim().toLowerCase();

export const filterAgentsForSingleSelector = (
  agents: Agent[],
  query: string,
): Agent[] => {
  const normalizedQuery = normalizeSearchText(query);
  if (!normalizedQuery) {
    return agents;
  }

  return agents.filter((agent) =>
    (agent.name ?? "").toLowerCase().includes(normalizedQuery),
  );
};

export const shouldShowSingleSelectorEmptySearch = (
  allAgentsCount: number,
  query: string,
  filteredAgentsCount: number,
): boolean => {
  const normalizedQuery = normalizeSearchText(query);
  return (
    allAgentsCount > 0 &&
    normalizedQuery.length > 0 &&
    filteredAgentsCount === 0
  );
};
