/**
 * 智能体管理Hook
 * 提供智能体的CRUD操作和缓存管理
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { message } from "antd";
import api from "../services/api";
import type {
  Agent,
  AgentCreateRequest,
  AgentUpdateRequest,
  AgentVisibility,
} from "../types";
import {
  filterAgentsByType,
  loadAdminAgentList,
} from "../services/agentListService";
import {
  clearSharedAgentsCache,
  getSharedAgentsCache,
  getSharedAgentsRequest,
  clearSharedAgentsRequest,
  setSharedAgentsCache,
  setSharedAgentsRequest,
} from "../services/agentsSharedStore";

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

  // 辅助方法
  getAgentById: (id: string) => Agent | undefined;
  getAgentsByVisibility: (visibility: AgentVisibility) => Agent[];
  clearCache: () => void;
}

interface IntyUploadImageResponse {
  data?: {
    avatar_url?: string;
    url?: string;
  };
}

const isFile = (value: unknown): value is File => {
  return value instanceof File;
};

const CACHE_EXPIRY_MS = 30 * 60 * 1000; // 30分钟过期

const canUseLocalStorage = (): boolean => {
  return typeof localStorage !== "undefined";
};

const getCachedDataFromLocalStorage = (cacheKey: string): Agent[] | null => {
  if (!canUseLocalStorage()) {
    return null;
  }

  try {
    const cachedRaw = localStorage.getItem(cacheKey);
    const cacheTimeRaw = localStorage.getItem(`${cacheKey}_time`);

    if (!cachedRaw || !cacheTimeRaw) {
      return null;
    }

    const cacheTime = Number(cacheTimeRaw);
    const isExpired = Number.isNaN(cacheTime)
      ? true
      : Date.now() - cacheTime > CACHE_EXPIRY_MS;

    if (isExpired) {
      localStorage.removeItem(cacheKey);
      localStorage.removeItem(`${cacheKey}_time`);
      return null;
    }

    return JSON.parse(cachedRaw) as Agent[];
  } catch (error) {
    console.warn("读取缓存失败:", error);
    return null;
  }
};

const setCachedDataToLocalStorage = (cacheKey: string, data: Agent[]): void => {
  if (!canUseLocalStorage()) {
    return;
  }

  try {
    localStorage.setItem(cacheKey, JSON.stringify(data));
    localStorage.setItem(`${cacheKey}_time`, Date.now().toString());
  } catch (error) {
    console.warn("设置缓存失败:", error);
  }
};

const clearCachedDataFromLocalStorage = (cacheKey: string): void => {
  if (!canUseLocalStorage()) {
    return;
  }

  localStorage.removeItem(cacheKey);
  localStorage.removeItem(`${cacheKey}_time`);
};

const getInitialAgentsState = (
  enableCache: boolean,
  cacheKey: string,
): Agent[] => {
  if (!enableCache) {
    return [];
  }

  const sharedData = getSharedAgentsCache({
    cacheKey,
    maxAgeMs: CACHE_EXPIRY_MS,
  });
  if (sharedData) {
    return sharedData;
  }

  const localData = getCachedDataFromLocalStorage(cacheKey);
  if (localData) {
    setSharedAgentsCache(cacheKey, localData);
    return localData;
  }

  return [];
};

export const useAgents = (options: UseAgentsOptions = {}): UseAgentsReturn => {
  const {
    type = "all",
    autoLoad = true,
    enableCache = true,
    // 2026-01: 切换为管理员全量列表接口后，避免复用旧缓存导致“非管理员创建”为空
    cacheKey = `agents_cache_${type}_admin_list_v1`,
  } = options;

  // 状态管理
  const [agents, setAgents] = useState<Agent[]>(() =>
    getInitialAgentsState(enableCache, cacheKey),
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadRequestIdRef = useRef(0);

  // 缓存管理
  const getCachedData = useCallback((): Agent[] | null => {
    if (!enableCache) {
      return null;
    }

    // 关键步骤：优先读页面级共享内存缓存，保证跨页面切换不重复拉取
    const sharedData = getSharedAgentsCache({
      cacheKey,
      maxAgeMs: CACHE_EXPIRY_MS,
    });
    if (sharedData) {
      return sharedData;
    }

    const localData = getCachedDataFromLocalStorage(cacheKey);
    if (localData) {
      setSharedAgentsCache(cacheKey, localData);
      return localData;
    }

    return null;
  }, [enableCache, cacheKey]);

  const setCachedData = useCallback(
    (data: Agent[]) => {
      if (!enableCache) {
        return;
      }

      // 关键步骤：同步写入共享内存缓存和 localStorage 缓存
      setSharedAgentsCache(cacheKey, data);
      setCachedDataToLocalStorage(cacheKey, data);
    },
    [enableCache, cacheKey],
  );

  const clearCache = useCallback(() => {
    clearSharedAgentsCache(cacheKey);
    clearCachedDataFromLocalStorage(cacheKey);
  }, [cacheKey]);

  // 错误处理
  const handleError = useCallback((error: unknown, defaultMessage: string) => {
    const errorMessage = (error as Error)?.message || defaultMessage;
    setError(errorMessage);
    message.error(errorMessage);
    console.error(defaultMessage, error);
  }, []);

  // 加载智能体列表
  const loadAgents = useCallback(
    async (forceRefresh: boolean = false) => {
      const requestId = ++loadRequestIdRef.current;
      const isCurrentRequest = () => loadRequestIdRef.current === requestId;
      let currentLoadRequest: Promise<Agent[]> | null = null;

      try {
        setError(null);

        // 检查缓存
        if (!forceRefresh) {
          const cachedData = getCachedData();
          if (cachedData && isCurrentRequest()) {
            setAgents(cachedData);
            return;
          }

          // 关键步骤：如果同一缓存键已有进行中的全量加载任务，直接复用该请求，避免重复分页拉取
          const sharedLoadingRequest = getSharedAgentsRequest({
            cacheKey,
            maxAgeMs: CACHE_EXPIRY_MS,
          });
          if (sharedLoadingRequest) {
            setLoading(true);
            const sharedAgents = await sharedLoadingRequest;
            if (!isCurrentRequest()) {
              return;
            }
            setAgents(sharedAgents);
            setCachedData(sharedAgents);
            return;
          }
        }

        setLoading(true);
        let hasLoadedFirstBatch = false;

        // 关键步骤：把“全量分页加载”封装为共享 Promise，同一时刻只跑一条请求链
        currentLoadRequest = (async (): Promise<Agent[]> => {
          // 评测后台需要看到全量角色（包含非管理员创建的角色），使用管理员专用列表接口
          const allAgents = await loadAdminAgentList({
            shouldContinue: isCurrentRequest,
            onBatchLoaded: (accumulatedAgents) => {
              if (!isCurrentRequest()) {
                return;
              }

              const filteredAgents = filterAgentsByType(
                accumulatedAgents,
                type,
              );
              setAgents(filteredAgents);

              // 第一批返回后立即展示，避免长时间整页 loading
              if (!hasLoadedFirstBatch) {
                hasLoadedFirstBatch = true;
                setLoading(false);
              }
            },
          });

          return filterAgentsByType(allAgents, type);
        })();

        setSharedAgentsRequest(cacheKey, currentLoadRequest);
        const filteredAgents = await currentLoadRequest;

        if (!isCurrentRequest()) {
          return;
        }

        setAgents(filteredAgents);

        // 更新缓存
        setCachedData(filteredAgents);

        if (forceRefresh) {
          message.success(`智能体列表已刷新`);
        }
      } catch (error) {
        handleError(error, "获取智能体列表失败");
      } finally {
        if (currentLoadRequest) {
          clearSharedAgentsRequest({
            cacheKey,
            request: currentLoadRequest,
          });
        }
        if (isCurrentRequest()) {
          setLoading(false);
        }
      }
    },
    [type, cacheKey, getCachedData, setCachedData, handleError],
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

        // 头像上传逻辑说明：
        // 1. 在 AgentManagePage 的 handleCreateAgent 中，如果用户选择了头像文件，
        //    会先调用 api.agents.uploadAvatar 上传图片，获得 URL 后赋值给 agentData.avatar
        // 2. 因此，当数据传递到 createAgent 时，data.avatar 可能是两种情况：
        //    - File 对象：需要在这里上传（用于直接传入 File 的场景，如某些 API 调用）
        //    - 字符串 URL：已经在 AgentManagePage 中上传过了，直接使用，避免重复上传
        // 3. 通过类型守卫检查来区分这两种情况，只对 File 对象执行上传操作
        if (
          data.avatar &&
          typeof data.avatar !== "string" &&
          isFile(data.avatar)
        ) {
          // data.avatar 是 File 对象，需要上传
          try {
            const uploadResponse = (await api.agents.uploadAvatar(
              data.avatar,
              true,
            )) as IntyUploadImageResponse;
            console.log("uploadResponse:", uploadResponse);
            // 上传成功后，将返回的 avatar_url 和 url 赋值给 agentData
            (agentData as AgentCreateRequest).avatar = uploadResponse.data
              ?.avatar_url as string;
            (agentData as AgentCreateRequest).background = uploadResponse.data
              ?.url as string;
          } catch (error) {
            console.error("头像上传失败:", error);
            message.error("头像上传失败，但智能体创建将继续");
            // 移除avatar字段，避免发送File对象到后端
            delete agentData.avatar;
          }
        }
        // 如果 data.avatar 是字符串（URL），说明已经在 AgentManagePage 中上传过了
        // 直接使用该 URL，不需要再次上传，避免重复上传导致的错误
        // 此时 agentData.avatar 已经是字符串 URL，可以直接用于创建智能体的 API 调用

        // 确保voice_id字段被正确处理
        if (data.voice_id) {
          agentData.voice_id = data.voice_id;
        }

        const newAgent = (await api.agents.create(agentData)) ?? null;

        // 将新 agent 插入本地列表第 1 位，不重载全量列表
        if (newAgent) {
          setAgents((prev) => {
            const updatedAgents = filterAgentsByType([newAgent, ...prev], type);
            setCachedData(updatedAgents);
            return updatedAgents;
          });
        }

        message.success("智能体创建成功");
        return newAgent;
      } catch (error) {
        handleError(error, "创建智能体失败");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [handleError, setCachedData, type],
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
        // 检查 data.avatar 是否是 File 对象（需要上传）还是字符串 URL（已经上传过了）
        if (
          data.avatar &&
          typeof data.avatar !== "string" &&
          isFile(data.avatar)
        ) {
          try {
            const uploadResponse = (await api.agents.uploadAvatar(
              data.avatar,
              true,
            )) as IntyUploadImageResponse;
            console.log("uploadResponse:", uploadResponse);
            (updateData as AgentUpdateRequest).avatar = uploadResponse.data
              ?.avatar_url as string;
            (updateData as AgentUpdateRequest).background = uploadResponse.data
              ?.url as string;

            const currentAgent = (await api.agents.get(agentId)) as Agent;
            if (
              currentAgent.extensions &&
              currentAgent.extensions.avatar_crop
            ) {
              const restExtensions = { ...currentAgent.extensions };
              delete restExtensions.avatar_crop;
              updateData.extensions =
                Object.keys(restExtensions).length > 0 ? restExtensions : null;
              console.log("已清除 avatar_crop 扩展信息");
            }
          } catch (error) {
            console.error("头像上传失败:", error);
            message.error("头像上传失败，但智能体更新将继续");
            // 移除avatar字段，避免发送File对象
            delete updateData.avatar;
          }
        }
        // 如果 data.avatar 是字符串（URL），说明已经上传过了，直接使用，不需要再次上传

        // 确保voice_id字段被正确处理
        if (data.voice_id !== undefined) {
          updateData.voice_id = data.voice_id;
        }

        const updatedAgent = (await api.agents.update(
          agentId,
          updateData,
        )) as Agent;

        // 仅更新本地内存态，避免保存动作被“全量分页刷新列表”阻塞
        setAgents((prevAgents) => {
          const mergedAgents = prevAgents.map((agent) => {
            if (agent.id !== agentId) {
              return agent;
            }
            return { ...agent, ...updatedAgent };
          });
          const filteredAgents = filterAgentsByType(mergedAgents, type);
          setCachedData(filteredAgents);
          return filteredAgents;
        });

        message.success("智能体更新成功");
        return updatedAgent;
      } catch (error) {
        handleError(error, "更新智能体失败");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [handleError, setCachedData, type],
  );

  // 删除智能体
  const deleteAgent = useCallback(
    async (agentId: string): Promise<boolean> => {
      try {
        setLoading(true);
        setError(null);

        await api.agents.delete(agentId);

        // 更新本地状态
        setAgents((prev) => {
          const filteredAgents = prev.filter((agent) => agent.id !== agentId);
          setCachedData(filteredAgents);
          return filteredAgents;
        });

        message.success("智能体已删除");
        return true;
      } catch (error) {
        handleError(error, "删除智能体失败");
        return false;
      } finally {
        setLoading(false);
      }
    },
    [handleError, setCachedData],
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

    // 辅助方法
    getAgentById,
    getAgentsByVisibility,
    clearCache,
  };
};
