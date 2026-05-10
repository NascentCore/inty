import { filterAgentsByName } from "./agentFilters";

const normalizeSearchText = (value: string): string =>
  value.trim().toLowerCase();

export const filterAgentsForSingleSelector = filterAgentsByName;

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
