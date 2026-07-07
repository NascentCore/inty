/**
 * CREATED_BY_AGENT
 */
import type { Agent } from "../types";

const normalizeSearchTerm = (term: string): string => term.trim().toLowerCase();

export const filterAgentsByName = (agents: Agent[], query: string): Agent[] => {
  const normalizedQuery = normalizeSearchTerm(query);
  if (!normalizedQuery) {
    return agents;
  }

  return agents.filter((agent) =>
    (agent.name ?? "").toLowerCase().includes(normalizedQuery),
  );
};
