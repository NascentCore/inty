/**
 * 智能体管理Hook
 * 提供智能体的CRUD操作和缓存管理
 */

import { useState, useEffect, useCallback } from "react";
import { message } from "antd";
import api from "../services/api";
import type {
  Agent,
  AgentCreateRequest,
  AgentUpdateRequest,
} from "../types";
import type { AgentVisibility } from "../inty_sdk/src/resources/api/v1/ai/agents";

interface UseAgentsOptions {
  type?: "public" | "private" | "all";
  autoLoad?: boolean;
  enableCache?: boolean;
  cacheKey?: string;
  useRecommended?: boolean; // 是否使用推荐API
}

interface UseAgentsReturn {
  // 状态
  agents: Agent[];
  loading: boolean;
  error: string | null;

  // 操作
  loadAgents: (forceRefresh?: boolean) => Promise<void>;
  createAgent: (
    data: AgentCreateRequest & { avatar?: File },
  ) => Promise<Agent | null>;
  updateAgent: (
    agentId: string,
    data: Partial<AgentUpdateRequest> & { avatar?: File },
  ) => Promise<Agent | null>;
  deleteAgent: (agentId: string) => Promise<boolean>;
  deployAgent: (agentId: string, adminPassword: string) => Promise<boolean>;

  // 辅助方法
  getAgentById: (id: string) => Agent | undefined;
  getAgentsByVisibility: (visibility: AgentVisibility) => Agent[];
  clearCache: () => void;
}

export const useAgents = (options: UseAgentsOptions = {}): UseAgentsReturn => {
  const {
    type = "all",
    autoLoad = true,
    enableCache = true,
    cacheKey = `agents_cache_${type}`,
  } = options;

  // 状态管理
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 缓存管理
  const CACHE_EXPIRY = 30 * 60 * 1000; // 30分钟过期

  const getCachedData = useCallback((): Agent[] | null => {
    if (!enableCache) return null;

    try {
      const cached = localStorage.getItem(cacheKey);
      const cacheTime = localStorage.getItem(`${cacheKey}_time`);

      if (cached && cacheTime) {
        const isExpired = Date.now() - parseInt(cacheTime) > CACHE_EXPIRY;
        if (!isExpired) {
          return JSON.parse(cached);
        }
      }
    } catch (error) {
      console.warn("读取缓存失败:", error);
    }

    return null;
  }, [enableCache, cacheKey, CACHE_EXPIRY]);

  const setCachedData = useCallback(
    (data: Agent[]) => {
      if (!enableCache) return;

      try {
        localStorage.setItem(cacheKey, JSON.stringify(data));
        localStorage.setItem(`${cacheKey}_time`, Date.now().toString());
      } catch (error) {
        console.warn("设置缓存失败:", error);
      }
    },
    [enableCache, cacheKey],
  );

  const clearCache = useCallback(() => {
    localStorage.removeItem(cacheKey);
    localStorage.removeItem(`${cacheKey}_time`);
  }, [cacheKey]);

  // 错误处理
  const handleError = useCallback((error: any, defaultMessage: string) => {
    const errorMessage = error?.message || defaultMessage;
    setError(errorMessage);
    message.error(errorMessage);
    console.error(defaultMessage, error);
  }, []);

  // 加载智能体列表
  const loadAgents = useCallback(
    async (forceRefresh: boolean = false) => {
      console.log("loadAgents called with forceRefresh:", forceRefresh);
      try {
        setLoading(true);
        setError(null);

        // 检查缓存
        if (!forceRefresh) {
          const cachedData = getCachedData();
          if (cachedData) {
            setAgents(cachedData);
            setLoading(false);
            console.log("cachedData:", cachedData);
            return;
          }
        }

        let response = await api.inty.api.v1.ai.agents.list({
          // 增加限制以获取更多智能体；后端限制最多 1000 个，这是分页设计；以后需要调整
          limit: 1000,
          skip: 0
        });
        let data = response.data;
        console.log("agent data:", data, "total:", data?.length);

        if (type !== "all" && Array.isArray(data)) {
          data = data.filter((agent) => {
            if (type === "public")
              return (
                agent.visibility === "PUBLIC"
              );
            if (type === "private")
              return (
                agent.visibility === "PRIVATE"
              );
            return true;
          });
        }
        console.log("agent data after filtering:", data);

        setAgents((data || []) as unknown as Agent[]);

        // 更新缓存
        setCachedData((data || []) as unknown as Agent[]);

        if (forceRefresh) {
          message.success(`智能体列表已刷新`);
        }
      } catch (error) {
        handleError(error, "获取智能体列表失败");
      } finally {
        setLoading(false);
      }
    },
    [type, getCachedData, setCachedData, handleError],
  );

  // 创建智能体
  const createAgent = useCallback(
    async (
      data: AgentCreateRequest & { avatar?: File },
    ): Promise<Agent | null> => {
      try {
        setLoading(true);
        setError(null);

        let agentData = { ...data };

        // 如果有头像文件，先上传头像
        if (data.avatar) {
          try {
            const { ...restData } = agentData;
            agentData = restData;
          } catch (error) {
            console.error("头像上传失败:", error);
            message.error("头像上传失败，但智能体创建将继续");
          }
        }

        // 确保voice_id字段被正确处理
        if (data.voice_id) {
          agentData.voice_id = data.voice_id;
        }

        const newAgent = await api.agents.create(agentData);

        // 更新本地状态
        setAgents((prev) => [newAgent, ...prev]);

        // 清理缓存
        clearCache();

        message.success("智能体创建成功");
        return newAgent;
      } catch (error) {
        handleError(error, "创建智能体失败");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [clearCache, handleError],
  );

  // 更新智能体
  const updateAgent = useCallback(
    async (
      agentId: string,
      data: Partial<AgentUpdateRequest> & { avatar?: File },
    ): Promise<Agent | null> => {
      try {
        setLoading(true);
        setError(null);

        let updateData = { ...data };

        // 如果有头像文件，先上传头像
        if (data.avatar) {
          try {
            // 这里应该调用头像上传API
            // const uploadResult = await api.uploadAvatar(data.avatar);
            // updateData.avatar = uploadResult.url;

            // 暂时移除avatar字段
            const { ...restData } = updateData;
            updateData = restData;
          } catch (error) {
            console.error("头像上传失败:", error);
            message.error("头像上传失败");
            return null;
          }
        }

        // 确保voice_id字段被正确处理
        if (data.voice_id !== undefined) {
          updateData.voice_id = data.voice_id;
        }

        const updatedAgent = await api.agents.update(agentId, updateData);

        // 更新本地状态
        setAgents((prev) =>
          prev.map((agent) => (agent.id === agentId ? updatedAgent : agent)),
        );

        // 清理缓存
        clearCache();

        message.success("智能体更新成功");
        return updatedAgent;
      } catch (error) {
        handleError(error, "更新智能体失败");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [clearCache, handleError],
  );

  // 删除智能体
  const deleteAgent = useCallback(
    async (agentId: string): Promise<boolean> => {
      try {
        setLoading(true);
        setError(null);

        await api.agents.delete(agentId);

        // 更新本地状态
        setAgents((prev) => prev.filter((agent) => agent.id !== agentId));

        // 清理缓存
        clearCache();

        message.success("智能体已删除");
        return true;
      } catch (error) {
        handleError(error, "删除智能体失败");
        return false;
      } finally {
        setLoading(false);
      }
    },
    [clearCache, handleError],
  );

  // 部署智能体
  const deployAgent = useCallback(
    async (agentId: string, adminPassword: string): Promise<boolean> => {
      try {
        setLoading(true);
        setError(null);

        const result = await api.agents.deploy(agentId, adminPassword);

        if (result.success) {
          message.success(result.message);
          return true;
        } else {
          throw new Error(result.message);
        }
      } catch (error) {
        handleError(error, "部署智能体失败");
        return false;
      } finally {
        setLoading(false);
      }
    },
    [handleError],
  );

  // 辅助方法
  const getAgentById = useCallback(
    (id: string): Agent | undefined => {
      return agents.find((agent) => agent.id === id);
    },
    [agents],
  );

  const getAgentsByVisibility = useCallback(
    (visibility: AgentVisibility): Agent[] => {
      return agents.filter((agent) => agent.visibility === visibility);
    },
    [agents],
  );

  // 自动加载
  useEffect(() => {
    if (autoLoad) {
      loadAgents();
    }
  }, [autoLoad, loadAgents]);

  // 类型变化时重新加载
  useEffect(() => {
    if (autoLoad) {
      loadAgents();
    }
  }, [type, autoLoad, loadAgents]);

  return {
    // 状态
    agents,
    loading,
    error,

    // 操作
    loadAgents,
    createAgent,
    updateAgent,
    deleteAgent,
    deployAgent,

    // 辅助方法
    getAgentById,
    getAgentsByVisibility,
    clearCache,
  };
};
