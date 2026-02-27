import { agentApi } from "./api";
import type { Agent } from "../types";
import {
  AGENT_LIST_PAGE_SIZE,
  fetchAllAgentsWithPagination,
} from "../utils/agentPagination";

export type AgentListType = "all" | "public" | "private";

interface LoadPagedAgentListOptions {
  pageSize?: number;
  onBatchLoaded?: (accumulatedAgents: Agent[], batchAgents: Agent[]) => void;
  shouldContinue?: () => boolean;
}

interface LoadSelfAgentListOptions extends LoadPagedAgentListOptions {
  type?: AgentListType;
}

const toApiVisibilityType = (
  type: AgentListType,
): "public" | "private" | undefined => {
  if (type === "public") {
    return "public";
  }

  if (type === "private") {
    return "private";
  }

  return undefined;
};

export const filterAgentsByType = (
  agents: Agent[],
  type: AgentListType = "all",
): Agent[] => {
  if (type === "all") {
    return agents;
  }

  return agents.filter((agent) => {
    if (type === "public") {
      return agent.visibility === "PUBLIC";
    }

    if (type === "private") {
      return agent.visibility === "PRIVATE";
    }

    return true;
  });
};

export const loadAdminAgentList = async (
  options: LoadPagedAgentListOptions = {},
): Promise<Agent[]> => {
  const {
    pageSize = AGENT_LIST_PAGE_SIZE,
    onBatchLoaded,
    shouldContinue,
  } = options;

  return fetchAllAgentsWithPagination({
    pageSize,
    fetchPage: ({ skip, limit }) => agentApi.listAll({ skip, limit }),
    onBatchLoaded,
    shouldContinue,
  });
};

export const loadSelfAgentList = async (
  options: LoadSelfAgentListOptions = {},
): Promise<Agent[]> => {
  const {
    type = "all",
    pageSize = AGENT_LIST_PAGE_SIZE,
    onBatchLoaded,
    shouldContinue,
  } = options;

  return fetchAllAgentsWithPagination({
    pageSize,
    fetchPage: ({ skip, limit }) =>
      agentApi.list({
        type: toApiVisibilityType(type),
        skip,
        limit,
      }),
    onBatchLoaded,
    shouldContinue,
  });
};
