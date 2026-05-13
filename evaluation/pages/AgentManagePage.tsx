import React, {
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
} from "react";
import {
  Card,
  Button,
  Input,
  InputNumber,
  Upload,
  Select,
  Row,
  Col,
  List,
  message,
  Spin,
  Space,
  Tag,
  Modal,
  Form,
  Radio,
  Popconfirm,
  Tooltip,
  Empty,
  Pagination,
  Divider,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CameraOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import type { UploadProps } from "antd";
import api, { logError } from "../services/api";
import modelCacheService from "../services/modelCache";
import type {
  Agent,
  AgentCreateRequest,
  AgentUpdateRequest,
  AvatarCropData,
  ExclusivePhotoItem,
  OpenRouterModel,
} from "../types";
import LLMConfigForm from "../components/common/LLMConfigForm";
import VoiceSelector from "../components/common/VoiceSelector";
import ScoreSelector from "../components/common/ScoreSelector";
import { useAgents } from "../hooks/useAgents";
import AgentDetailModal from "../components/common/AgentDetailModal";
import { generateRandomName } from "../utils/nameGenerator";
import { hasAgentChanged } from "../utils/agentComparison";
import ImageCropModal from "../components/common/ImageCropModal";
import BackgroundCropModal from "../components/common/BackgroundCropModal";
import AvatarDisplay from "../components/common/AvatarDisplay";
import {
  buildAgentProfilePageHash,
  getDeepLinkedAgentIdFromHash,
} from "../utils/profileLinks";

const { TextArea } = Input;
const { Search } = Input;
const { Option } = Select;

/** Show info dialog after agent data is saved: cache may take time to refresh. */
function showAgentSavedCacheNotice() {
  Modal.info({
    title: "Saved",
    content:
      "Agent data has been saved. It may take some time for the cache to refresh before changes appear everywhere.",
    okText: "OK",
  });
}

// 类型已在 types.ts 中定义

export const AgentManagePage: React.FC = () => {
  // 使用 useAgents hook
  const {
    agents,
    loading,
    loadAgents: loadAgentsFromHook,
    createAgent: createAgentFromHook,
    updateAgent: updateAgentFromHook,
    deleteAgent: deleteAgentFromHook,
  } = useAgents({
    type: "all",
    autoLoad: false, // 手动控制加载
  });

  // 状态管理
  const [localAgents, setLocalAgents] = useState<Agent[]>([]);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<Agent | null>(null);
  const [saveLoading, setSaveLoading] = useState(false);

  // 搜索和筛选
  const [searchText, setSearchText] = useState("");
  const [visibilityFilter, setVisibilityFilter] = useState<string>("all");
  const [genderFilter, setGenderFilter] = useState<string>("all");
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [backgroundAnimatedFilter, setBackgroundAnimatedFilter] =
    useState<string>("all");
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [creatorFilter, setCreatorFilter] = useState<string>("admin");
  const [deepLinkedAgentId, setDeepLinkedAgentId] = useState(() => {
    if (typeof window === "undefined") {
      return "";
    }
    return getDeepLinkedAgentIdFromHash(window.location.hash);
  });
  const hasAppliedAgentDeepLinkRef = useRef(false);

  // 分页
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 12,
    total: 0,
  });

  // 表单和文件上传
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string>("");
  const [editAvatarFile, setEditAvatarFile] = useState<File | null>(null);
  const [agentCopy, setAgentCopy] = useState<Agent | null>(null);

  // 检查是否有变化
  const hasChanges = hasAgentChanged(currentAgent, agentCopy);

  // 监听表单变化，更新 agent_copy
  const handleFormChange = (
    changedValues: Record<string, unknown>,
    allValues: Record<string, unknown>,
  ) => {
    if (!agentCopy) return;

    // 构建新的 agent_copy
    const newAgentCopy = {
      ...agentCopy,
      ...changedValues,
    };

    // 处理 LLM 配置
    if (allValues.modelType === "custom") {
      newAgentCopy.llm_config = {
        model: (allValues.model as string) || "gpt-4o",
        temperature: (allValues.temperature as number) || 0.7,
        max_tokens: (allValues.max_tokens as number) || 2048,
        top_p: (allValues.top_p as number) || 1,
        frequency_penalty: (allValues.frequency_penalty as number) || 0,
        presence_penalty: (allValues.presence_penalty as number) || 0,
      };
    } else {
      newAgentCopy.llm_config = null;
    }

    setAgentCopy(newAgentCopy);
  };

  // 修改头像弹窗状态（列表中的修改头像按钮）
  const [avatarCropModalVisible, setAvatarCropModalVisible] = useState(false);
  const [avatarCropImageSrc, setAvatarCropImageSrc] = useState<string>("");
  const [currentAgentForAvatar, setCurrentAgentForAvatar] =
    useState<Agent | null>(null);

  // 创建模式头像截取弹窗状态
  const [createAvatarCropModalVisible, setCreateAvatarCropModalVisible] =
    useState(false);
  const [createAvatarCropImageSrc, setCreateAvatarCropImageSrc] =
    useState<string>("");
  const [createAvatarCropData, setCreateAvatarCropData] =
    useState<AvatarCropData | null>(null);

  // 编辑模式头像截取弹窗状态
  const [editAvatarCropModalVisible, setEditAvatarCropModalVisible] =
    useState(false);
  const [editAvatarCropImageSrc, setEditAvatarCropImageSrc] =
    useState<string>("");

  // 模型相关状态
  const [openRouterModels, setOpenRouterModels] = useState<OpenRouterModel[]>(
    [],
  );
  const [modelsLoading, setModelsLoading] = useState(false);

  // Prompt 相关状态
  const [availablePrompts, setAvailablePrompts] = useState<{
    main_prompts: Array<{
      id: string;
      name: string;
      description: string;
      content?: string;
    }>;
    mode_prompts: Array<{
      id: string;
      name: string;
      description: string;
      content?: string;
    }>;
    force_default_prompts: boolean;
    default_main_prompt_id: string;
    default_mode_prompt_id: string;
  } | null>(null);
  const [promptsLoading, setPromptsLoading] = useState(false);

  // 背景视频相关状态
  const [backgroundAnimatedFile, setBackgroundAnimatedFile] =
    useState<File | null>(null);
  const [backgroundAnimatedPreview, setBackgroundAnimatedPreview] =
    useState<string>("");
  const [generateAnimatedModalVisible, setGenerateAnimatedModalVisible] =
    useState(false);
  const [generateAnimatedLoading, setGenerateAnimatedLoading] = useState(false);
  const [generateAnimatedPrompt, setGenerateAnimatedPrompt] = useState("");
  const [backgroundCropModalVisible, setBackgroundCropModalVisible] =
    useState(false);
  const [pendingGenerateAction, setPendingGenerateAction] = useState<{
    agentId: string;
    prompt?: string;
  } | null>(null);

  // 判断URL是否为视频格式
  const isVideoUrl = (url: string | undefined): boolean => {
    if (!url) return false;
    const urlLower = url.toLowerCase();

    // 检查是否为data URL，如果是video类型
    if (urlLower.startsWith("data:video/")) {
      return true;
    }

    // 检查文件扩展名（更精确的匹配）
    const videoExtensions = [
      ".mp4",
      ".webm",
      ".mov",
      ".avi",
      ".mkv",
      ".flv",
      ".wmv",
      ".m4v",
    ];
    const imageExtensions = [
      ".gif",
      ".avif",
      ".jpg",
      ".jpeg",
      ".png",
      ".webp",
      ".bmp",
      ".svg",
    ];

    // 先检查是否为图片格式（向后兼容）
    // 使用更精确的匹配，检查扩展名是否在URL末尾或后面跟着查询参数
    const urlWithoutQuery = urlLower.split("?")[0];
    if (imageExtensions.some((ext) => urlWithoutQuery.endsWith(ext))) {
      return false;
    }

    // 检查是否为视频格式
    if (videoExtensions.some((ext) => urlWithoutQuery.endsWith(ext))) {
      return true;
    }

    // 检查URL路径中是否包含视频相关路径（更精确）
    if (urlLower.includes("/videos/") || urlLower.includes("/video/")) {
      return true;
    }

    // 默认返回false，保持向后兼容
    return false;
  };

  // 加载智能体列表
  const loadAgents = useCallback(
    async (forceRefresh = false) => {
      if (forceRefresh) {
        setPagination((prev) => ({ ...prev, current: 1 }));
      }

      // 首次进入页面使用共享缓存，手动点击刷新时才强制重载
      await loadAgentsFromHook(forceRefresh);
    },
    [loadAgentsFromHook],
  );

  // 加载模型列表
  const loadModels = useCallback(async () => {
    setModelsLoading(true);
    try {
      const models = await modelCacheService.getOpenRouterModels();
      setOpenRouterModels(models);
    } catch (error) {
      console.error("加载模型列表失败:", error);
      message.error("加载模型列表失败");
    } finally {
      setModelsLoading(false);
    }
  }, []);

  // 刷新模型列表
  const handleRefreshModels = useCallback(() => {
    loadModels();
    message.success("正在刷新模型列表...");
  }, [loadModels]);

  // 加载可用 prompt 列表
  const loadAvailablePrompts = useCallback(async () => {
    setPromptsLoading(true);
    try {
      // 使用 agentApi 获取 prompt 列表
      const data = await api.agents.getAvailablePrompts({
        include_content: true,
      });
      console.log("Prompt data:", data);
      console.log("Main prompts:", data?.main_prompts);
      console.log("Mode prompts:", data?.mode_prompts);
      if (data && (data.main_prompts || data.mode_prompts)) {
        setAvailablePrompts(data);
      } else {
        console.error("加载 prompt 列表失败: 数据格式不正确", data);
        message.error("加载 prompt 列表失败");
      }
    } catch (error) {
      console.error("加载 prompt 列表失败:", error);
      message.error("加载 prompt 列表失败");
    } finally {
      setPromptsLoading(false);
    }
  }, []);

  const allTags = useMemo(() => {
    if (!agents || agents.length === 0) {
      return [];
    }
    const tagSet = new Set<string>();
    agents.forEach((agent) => {
      (agent.tags || []).forEach((tag) => {
        if (tag) {
          tagSet.add(tag);
        }
      });
    });
    return Array.from(tagSet).sort((a, b) => a.localeCompare(b));
  }, [agents]);

  // 监听 agents 变化，应用筛选
  useEffect(() => {
    let filteredAgents = agents || [];

    const normalizedSearchText = searchText.trim().toLowerCase();

    // 搜索筛选
    if (normalizedSearchText) {
      filteredAgents = filteredAgents.filter((agent) => {
        const idMatch = agent.id.toLowerCase().includes(normalizedSearchText);
        const nameMatch = agent.name
          ?.toLowerCase()
          .includes(normalizedSearchText);
        const introMatch = agent.intro
          ? agent.intro.toLowerCase().includes(normalizedSearchText)
          : false;
        return idMatch || nameMatch || introMatch;
      });
    }

    // 可见性筛选
    if (visibilityFilter !== "all") {
      filteredAgents = filteredAgents.filter(
        (agent) => agent.visibility === visibilityFilter.toUpperCase(),
      );
    }

    // 性别筛选
    if (genderFilter !== "all") {
      filteredAgents = filteredAgents.filter(
        (agent) => agent.gender === genderFilter.toUpperCase(),
      );
    }

    // 标签筛选（需要全部匹配）
    const normalizedTagFilter = tagFilter
      .map((tag) => tag.trim().toLowerCase())
      .filter((tag) => tag.length > 0);
    if (normalizedTagFilter.length > 0) {
      filteredAgents = filteredAgents.filter((agent) => {
        const agentTags = (agent.tags || [])
          .filter((tag): tag is string => Boolean(tag))
          .map((tag) => tag.toLowerCase());
        return normalizedTagFilter.every((selectedTag) =>
          agentTags.includes(selectedTag),
        );
      });
    }

    // 背景动图筛选
    if (backgroundAnimatedFilter !== "all") {
      filteredAgents = filteredAgents.filter((agent) => {
        const hasAnimated =
          agent.background_animated &&
          agent.background_animated.trim().length > 0;
        if (backgroundAnimatedFilter === "yes") {
          return hasAnimated;
        } else if (backgroundAnimatedFilter === "no") {
          return !hasAnimated;
        }
        return true;
      });
    }

    // 来源筛选
    if (sourceFilter !== "all") {
      filteredAgents = filteredAgents.filter(
        (agent) => agent.source === sourceFilter,
      );
    }

    // 创建者类型筛选
    if (creatorFilter !== "all") {
      filteredAgents = filteredAgents.filter((agent) => {
        const isSuperuser = agent.creator?.is_superuser ?? false;
        if (creatorFilter === "admin") {
          return isSuperuser;
        } else if (creatorFilter === "non-admin") {
          return !isSuperuser;
        }
        return true;
      });
    }

    setLocalAgents(filteredAgents);
    setPagination((prev) => ({
      ...prev,
      total: filteredAgents.length,
    }));
  }, [
    agents,
    searchText,
    visibilityFilter,
    genderFilter,
    tagFilter,
    backgroundAnimatedFilter,
    sourceFilter,
    creatorFilter,
  ]);

  useEffect(() => {
    // 关键步骤：如果 useAgents 已经从共享缓存恢复了全量 agents，进入页面时不再重复触发全量加载
    if (agents.length === 0) {
      loadAgents();
    }
    loadModels(); // 加载模型列表
    loadAvailablePrompts(); // 加载 prompt 列表
  }, [agents.length, loadAgents, loadModels, loadAvailablePrompts]);

  useEffect(() => {
    const syncDeepLinkedAgentId = () => {
      setDeepLinkedAgentId(getDeepLinkedAgentIdFromHash(window.location.hash));
    };
    window.addEventListener("hashchange", syncDeepLinkedAgentId);
    return () =>
      window.removeEventListener("hashchange", syncDeepLinkedAgentId);
  }, []);

  useEffect(() => {
    hasAppliedAgentDeepLinkRef.current = false;
  }, [deepLinkedAgentId]);

  useEffect(() => {
    if (!deepLinkedAgentId) {
      return;
    }
    setSearchText(deepLinkedAgentId);
    setPagination((prev) => ({ ...prev, current: 1 }));
  }, [deepLinkedAgentId]);

  useEffect(() => {
    if (!deepLinkedAgentId || hasAppliedAgentDeepLinkRef.current) {
      return;
    }
    if (agents.length === 0) {
      return;
    }
    hasAppliedAgentDeepLinkRef.current = true;
    const matchedAgent = agents.find((agent) => agent.id === deepLinkedAgentId);
    if (matchedAgent) {
      setCurrentAgent(matchedAgent);
      setDetailModalVisible(true);
    }
  }, [agents, deepLinkedAgentId]);

  // 处理头像上传（创建模式，打开截取弹窗）
  const handleAvatarChange: UploadProps["beforeUpload"] = (file) => {
    const isImage = file.type.startsWith("image/");
    if (!isImage) {
      message.error("只能上传图片文件!");
      return false;
    }

    setAvatarFile(file);
    const reader = new FileReader();
    reader.onload = (e) => {
      const imageUrl = e.target?.result as string;
      setCreateAvatarCropImageSrc(imageUrl);
      setCreateAvatarCropModalVisible(true);
    };
    reader.readAsDataURL(file);
    return false;
  };

  // 处理编辑头像上传（编辑模式，打开截取弹窗）
  const handleEditAvatarChange: UploadProps["beforeUpload"] = (file) => {
    const isImage = file.type.startsWith("image/");
    if (!isImage) {
      message.error("只能上传图片文件!");
      return false;
    }

    setEditAvatarFile(file);
    const reader = new FileReader();
    reader.onload = (e) => {
      const imageUrl = e.target?.result as string;
      setEditAvatarCropImageSrc(imageUrl);
      setEditAvatarCropModalVisible(true);
    };
    reader.readAsDataURL(file);
    return false;
  };

  // 处理修改头像截取
  const handleAvatarCrop = (agent: Agent) => {
    // 检查是否有背景图
    if (!agent.background) {
      message.warning("该角色没有背景图，无法修改头像");
      return;
    }

    // 使用背景图作为截取源头
    const backgroundImage = agent.background;
    setCurrentAgentForAvatar(agent);
    setAvatarCropImageSrc(backgroundImage);
    setAvatarCropModalVisible(true);
  };

  // 处理头像截取确认（仅更新本地状态，不触发 loadAgents，与编辑弹窗保存一致）
  const handleAvatarCropConfirm = async (cropData: AvatarCropData) => {
    if (!currentAgentForAvatar) return;

    try {
      const updatedAgent = await updateAgentFromHook(currentAgentForAvatar.id, {
        extensions: { avatar_crop: cropData },
      });
      if (updatedAgent) {
        message.success("头像坐标设置成功");
        showAgentSavedCacheNotice();
      }
    } finally {
      setAvatarCropModalVisible(false);
      setAvatarCropImageSrc("");
      setCurrentAgentForAvatar(null);
    }
  };

  // 处理头像截取取消
  const handleAvatarCropCancel = () => {
    setAvatarCropModalVisible(false);
    setAvatarCropImageSrc("");
    setCurrentAgentForAvatar(null);
  };

  // 处理创建模式头像截取确认
  const handleCreateAvatarCropConfirm = (cropData: AvatarCropData) => {
    setCreateAvatarCropData(cropData);
    setAvatarPreview(createAvatarCropImageSrc);
    setCreateAvatarCropModalVisible(false);
    setCreateAvatarCropImageSrc("");
  };

  // 处理创建模式头像截取取消
  const handleCreateAvatarCropCancel = () => {
    setCreateAvatarCropModalVisible(false);
    setCreateAvatarCropImageSrc("");
    setAvatarFile(null);
  };

  // 处理编辑模式头像截取确认
  const handleEditAvatarCropConfirm = (cropData: AvatarCropData) => {
    if (agentCopy) {
      setAgentCopy({
        ...agentCopy,
        avatar: undefined,
        background: editAvatarCropImageSrc,
        extensions: {
          ...agentCopy.extensions,
          avatar_crop: cropData,
        },
      });
    }
    setEditAvatarCropModalVisible(false);
    setEditAvatarCropImageSrc("");
  };

  // 处理编辑模式头像截取取消
  const handleEditAvatarCropCancel = () => {
    setEditAvatarCropModalVisible(false);
    setEditAvatarCropImageSrc("");
    setEditAvatarFile(null);
  };

  // 打开生成背景动图模态框时检查比例
  const handleOpenGenerateAnimatedModal = async () => {
    if (!currentAgent) {
      message.warning("请先选择要编辑的角色");
      return;
    }

    if (!currentAgent.background) {
      message.warning("请先上传背景图");
      return;
    }

    try {
      // 检查背景图是否为 9:16 比例
      const aspectRatioInfo = await api.agents.checkBackgroundAspectRatio(
        currentAgent.id,
      );

      if (!aspectRatioInfo.is_9_16) {
        // 不是 9:16 比例，直接显示裁剪模态框，不显示生成模态框
        setPendingGenerateAction({
          agentId: currentAgent.id,
          prompt: generateAnimatedPrompt.trim() || undefined,
        });
        setBackgroundCropModalVisible(true);
        // 不打开生成模态框
        return;
      }

      // 是 9:16 比例，正常显示生成模态框
      setGenerateAnimatedModalVisible(true);
      setGenerateAnimatedPrompt("");
    } catch (error) {
      console.error("检查背景图宽高比失败:", error);
      message.error(
        `检查背景图宽高比失败: ${
          error instanceof Error ? error.message : "未知错误"
        }`,
      );
      // 检查失败时，仍然打开生成模态框，让用户尝试
      setGenerateAnimatedModalVisible(true);
      setGenerateAnimatedPrompt("");
    }
  };

  // 检查背景图宽高比并生成动图
  const checkAndGenerateBackgroundAnimated = async () => {
    if (!currentAgent) {
      message.warning("请先选择要编辑的角色");
      return false;
    }

    if (!currentAgent.background) {
      message.warning("请先上传背景图");
      return false;
    }

    try {
      // 检查背景图是否为 9:16 比例
      const aspectRatioInfo = await api.agents.checkBackgroundAspectRatio(
        currentAgent.id,
      );

      if (!aspectRatioInfo.is_9_16) {
        // 不是 9:16 比例，显示裁剪模态框
        setPendingGenerateAction({
          agentId: currentAgent.id,
          prompt: generateAnimatedPrompt.trim() || undefined,
        });
        setBackgroundCropModalVisible(true);
        return false; // 不关闭生成模态框
      }

      // 是 9:16 比例，直接生成
      return await doGenerateBackgroundAnimated(
        currentAgent.id,
        generateAnimatedPrompt.trim() || undefined,
      );
    } catch (error) {
      console.error("检查背景图宽高比失败:", error);
      message.error(
        `检查背景图宽高比失败: ${
          error instanceof Error ? error.message : "未知错误"
        }`,
      );
      return false;
    }
  };

  // 执行生成背景动图
  const doGenerateBackgroundAnimated = async (
    agentId: string,
    prompt?: string,
  ) => {
    try {
      setGenerateAnimatedLoading(true);
      console.log("开始调用 API", {
        agentId,
        prompt,
      });

      const updatedAgent = await api.agents.generateBackgroundAnimated(
        agentId,
        prompt,
      );

      console.log("API 调用成功", updatedAgent);

      if (updatedAgent && updatedAgent.background_animated) {
        // 更新 agent_copy
        if (agentCopy) {
          setAgentCopy({
            ...agentCopy,
            background_animated: updatedAgent.background_animated,
          });
        }
        // 更新当前 agent
        if (currentAgent && currentAgent.id === agentId) {
          setCurrentAgent({
            ...currentAgent,
            background_animated: updatedAgent.background_animated,
          });
        }
        message.success("背景动图生成成功");
        showAgentSavedCacheNotice();
        setGenerateAnimatedModalVisible(false);
        setGenerateAnimatedPrompt("");
        return true;
      } else {
        message.error("背景动图生成失败");
        return false;
      }
    } catch (error) {
      console.error("生成背景动图失败:", error);
      message.error(
        `生成背景动图失败: ${
          error instanceof Error ? error.message : "未知错误"
        }`,
      );
      return false;
    } finally {
      setGenerateAnimatedLoading(false);
    }
  };

  // 处理生成背景视频（保留原函数名以兼容现有代码）
  const handleGenerateBackgroundAnimated = async () => {
    return await checkAndGenerateBackgroundAnimated();
  };

  // 处理背景图裁剪确认
  const handleBackgroundCropConfirm = async (croppedImageBlob: Blob) => {
    if (!pendingGenerateAction) {
      message.error("缺少生成参数");
      return;
    }

    try {
      setGenerateAnimatedLoading(true);
      setBackgroundCropModalVisible(false);

      // 将 Blob 转换为 File
      const croppedFile = new File(
        [croppedImageBlob],
        "cropped-background.jpg",
        { type: "image/jpeg" },
      );

      // 上传裁剪后的背景图
      message.info("正在上传裁剪后的背景图...");
      const updatedAgent = await api.agents.uploadCroppedBackground(
        pendingGenerateAction.agentId,
        croppedFile,
      );

      // 更新当前 agent 的背景图
      if (currentAgent && currentAgent.id === pendingGenerateAction.agentId) {
        setCurrentAgent({
          ...currentAgent,
          background: updatedAgent.background,
        });
      }

      message.success("背景图裁剪并上传成功");
      showAgentSavedCacheNotice();

      // 不再直接生成视频，而是打开生成视频模态框让用户填写提示词
      // 保留 pendingGenerateAction，以便在生成模态框中点击确认时继续
      setGenerateAnimatedModalVisible(true);
      // 如果之前有提示词，保留它；否则清空
      if (pendingGenerateAction.prompt) {
        setGenerateAnimatedPrompt(pendingGenerateAction.prompt);
      } else {
        setGenerateAnimatedPrompt("");
      }
    } catch (error) {
      console.error("上传裁剪后的背景图失败:", error);
      message.error(
        `上传裁剪后的背景图失败: ${
          error instanceof Error ? error.message : "未知错误"
        }`,
      );
      setPendingGenerateAction(null);
    } finally {
      setGenerateAnimatedLoading(false);
    }
  };

  // 处理背景图裁剪取消
  const handleBackgroundCropCancel = () => {
    setBackgroundCropModalVisible(false);
    setPendingGenerateAction(null);
  };

  // 创建智能体
  const handleCreateAgent = async () => {
    try {
      const values = await createForm.validateFields();

      setSaveLoading(true);

      const score = values.score;
      const comment = values.comment;

      // 从 values 中排除 UI 状态字段，只保留需要提交的数据
      const otherValues = { ...values };
      delete otherValues.score;
      delete otherValues.comment;
      delete otherValues.main_prompt_select;
      delete otherValues.mode_prompt_select;
      delete otherValues.main_prompt_display;
      delete otherValues.mode_prompt_display;

      const agentData: AgentCreateRequest = {
        ...otherValues,
        voice_id: values.voice_id,
        tags: values.tags || [],
      };

      // 如果有评分或备注，添加到 meta_data 中
      if (score || comment) {
        agentData.meta_data = {
          score: score,
          comment: comment,
        };
      }

      // 如果选择了自定义模型，添加LLM配置
      if (values.modelType === "custom") {
        agentData.llm_config = {
          model: values.model,
          temperature: values.temperature,
          max_tokens: values.max_tokens,
          top_p: values.top_p,
          frequency_penalty: values.frequency_penalty,
          presence_penalty: values.presence_penalty,
        };
      }

      // 处理头像文件
      // 注意：在创建角色时，我们在这里先上传图片获取 URL，然后将 URL 传递给 createAgent
      // 这样做的原因是：AgentManagePage 需要在上传成功后获得 URL 用于预览等操作
      // createAgent 函数会检查 data.avatar 的类型：
      // - 如果是 File 对象，会再次上传（用于直接传入 File 的场景）
      // - 如果是字符串 URL，说明已经上传过了，直接使用，不会重复上传
      if (avatarFile) {
        // 上传头像文件获取 URL
        const uploadResult = await api.agents.uploadAvatar(avatarFile, true);
        if (uploadResult && uploadResult.url) {
          // 将上传后的 URL 赋值给 agentData.avatar（此时是字符串，不是 File 对象）
          agentData.avatar = uploadResult.url;
        }
      }

      // 如果有截取数据，添加到 extensions 中
      if (createAvatarCropData) {
        agentData.extensions = {
          ...agentData.extensions,
          avatar_crop: createAvatarCropData,
        };
      }

      // 处理背景视频文件
      if (backgroundAnimatedFile) {
        // 上传视频文件
        const uploadResult = await api.agents.uploadAvatar(
          backgroundAnimatedFile,
          false,
        );
        if (uploadResult && uploadResult.url) {
          agentData.background_animated = uploadResult.url;
        }
      }

      // 使用 useAgents hook 的 createAgent 进行优化创建
      const newAgent = await createAgentFromHook(
        agentData as AgentCreateRequest & { avatar?: File },
      );

      if (newAgent) {
        // 成功创建，关闭弹窗并重置状态
        setCreateModalVisible(false);
        createForm.resetFields();
        setAvatarFile(null);
        setAvatarPreview("");
        setCreateAvatarCropData(null);
        showAgentSavedCacheNotice();
        // 不需要调用 loadAgents()，因为 createAgentFromHook 已经优化更新了本地状态
      } else {
        // 创建失败，保持弹窗打开让用户重试
        message.error("创建智能体失败，请检查网络连接后重试");
      }
    } catch (error) {
      console.error("创建智能体失败:", error);
      message.error("创建智能体失败，请重试");
    } finally {
      setSaveLoading(false);
    }
  };

  // 编辑智能体
  const handleEditAgent = async () => {
    if (!currentAgent) return;

    try {
      const values = await editForm.validateFields();
      setSaveLoading(true);

      const score = values.score;
      const comment = values.comment;

      // 从 values 中排除 UI 状态字段，只保留需要提交的数据
      const otherValues = { ...values };
      delete otherValues.score;
      delete otherValues.comment;
      delete otherValues.main_prompt_select;
      delete otherValues.mode_prompt_select;
      delete otherValues.main_prompt_display;
      delete otherValues.mode_prompt_display;

      const updateData = {
        ...otherValues,
        voice_id: values.voice_id,
        tags: values.tags || [],
      };

      // 处理评分和备注更新
      if (score !== undefined || comment !== undefined) {
        updateData.meta_data = {
          score: score,
          comment: comment,
        };
      } else {
        // 如果没有评分和备注，确保清空 meta_data
        updateData.meta_data = undefined;
      }

      // 如果选择了自定义模型，添加LLM配置
      if (values.modelType === "custom") {
        updateData.llm_config = {
          model: values.model,
          temperature: values.temperature,
          max_tokens: values.max_tokens,
          top_p: values.top_p,
          frequency_penalty: values.frequency_penalty,
          presence_penalty: values.presence_penalty,
        };
      }

      if (values.modelType === "default") {
        // 选择默认模型时，显式设置为null
        updateData.llm_config = null;
      }

      // 处理头像文件
      if (editAvatarFile) {
        updateData.avatar = editAvatarFile;
      }

      // 如果 agentCopy 有 extensions.avatar_crop，添加到更新数据中
      if (agentCopy?.extensions?.avatar_crop) {
        updateData.extensions = {
          ...updateData.extensions,
          avatar_crop: agentCopy.extensions.avatar_crop,
        };
      }

      // 处理背景视频文件
      if (backgroundAnimatedFile) {
        // 上传视频文件
        const uploadResult = await api.agents.uploadAvatar(
          backgroundAnimatedFile,
          false,
        );
        if (uploadResult && uploadResult.url) {
          updateData.background_animated = uploadResult.url;
        }
      }

      // 如果 agent_copy 中有 background_animated，使用它（可能是直接设置的 URL）
      if (agentCopy?.background_animated) {
        updateData.background_animated = agentCopy.background_animated;
      } else if (
        currentAgent?.background_animated &&
        !agentCopy?.background_animated &&
        !backgroundAnimatedFile
      ) {
        // 处理背景动图删除：原来有动图 + 现在没有了 + 没有新上传的文件 = 用户要删除动图
        updateData.background_animated = "";
      }

      if (agentCopy?.exclusive_photos) {
        updateData.exclusive_photos = agentCopy.exclusive_photos;
      }

      // 使用 useAgents hook 的 updateAgent 进行优化更新
      const updatedAgent = await updateAgentFromHook(
        currentAgent.id,
        updateData,
      );

      if (updatedAgent) {
        // 成功更新，关闭弹窗并重置状态
        setEditModalVisible(false);
        setCurrentAgent(null);
        setAgentCopy(null);
        editForm.resetFields();
        setEditAvatarFile(null);
        showAgentSavedCacheNotice();
        // 不需要调用 loadAgents()，因为 updateAgentFromHook 已经优化更新了本地状态
      } else {
        // 更新失败，保持弹窗打开让用户重试
        message.error("更新智能体失败，请检查网络连接后重试");
      }
    } catch (error) {
      console.error("更新智能体失败:", error);
      message.error("更新智能体失败，请重试");
    } finally {
      setSaveLoading(false);
    }
  };

  // 删除智能体
  const handleDeleteAgent = async (agent: Agent) => {
    try {
      await deleteAgentFromHook(agent.id);
    } catch (error) {
      console.error("删除智能体失败:", error);
      message.error("删除智能体失败，请重试");
    }
  };

  // 删除背景图
  const handleDeleteBackgroundImage = async (imageUrl: string) => {
    if (!currentAgent) return;

    Modal.confirm({
      title: "确认删除",
      content: "确定要删除这张背景图吗？此操作不可恢复。",
      okText: "删除",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        try {
          const filteredImages = (currentAgent.background_images || []).filter(
            (img) => img !== imageUrl,
          );

          // 直接调用 API，使用 replace_background_images 参数来替换而非追加
          const updatePayload: AgentUpdateRequest & {
            replace_background_images: boolean;
          } = {
            background_images: filteredImages,
            replace_background_images: true,
          };

          const updatedAgent = (await api.agents.update(
            currentAgent.id,
            updatePayload,
          )) as Agent;

          if (updatedAgent) {
            setCurrentAgent({
              ...currentAgent,
              background_images: filteredImages,
            });
            message.success("背景图已删除");
            showAgentSavedCacheNotice();
          }
        } catch (error) {
          console.error("删除背景图失败:", error);
          message.error("删除背景图失败，请重试");
        }
      },
    });
  };

  // 设置创建表单的默认值
  const setCreateFormDefaults = () => {
    setTimeout(() => {
      const gender = "FEMALE";
      const randomName = generateRandomName(
        gender as "MALE" | "FEMALE" | "OTHER",
      );
      const defaultValues = {
        name: randomName,
        gender: gender,
        visibility: "PRIVATE",
        modelType: "default",
        voice_id: undefined,
      };
      createForm.setFieldsValue(defaultValues);
    }, 100);
  };

  // 随机生成角色名字
  const generateRandomNameForForm = () => {
    const currentGender = createForm.getFieldValue("gender") || "FEMALE";
    const randomName = generateRandomName(
      currentGender as "MALE" | "FEMALE" | "OTHER",
    );
    createForm.setFieldValue("name", randomName);
  };

  // 随机生成角色名字（编辑表单）
  const generateRandomNameForEditForm = () => {
    const currentGender = editForm.getFieldValue("gender") || "FEMALE";
    const randomName = generateRandomName(
      currentGender as "MALE" | "FEMALE" | "OTHER",
    );
    editForm.setFieldValue("name", randomName);
  };

  // 显示编辑模态框
  const showEditModal = (agent: Agent) => {
    setCurrentAgent(agent);
    // 深拷贝 agent 数据到 agent_copy
    setAgentCopy({
      ...agent,
      extensions: agent.extensions ? { ...agent.extensions } : undefined,
      background_animated: agent.background_animated,
      exclusive_photos: agent.exclusive_photos ?? [],
    });

    // 预填表单 - 使用 setTimeout 确保 Modal 完全渲染后再设置表单值
    setTimeout(() => {
      // 判断 main_prompt 和 mode_prompt 是预设 ID 还是自定义文本
      let mainPromptSelect: string | null = null;
      let mainPromptDisplay: string | null = null;
      let modePromptSelect: string | null = null;
      let modePromptDisplay: string | null = null;

      if (availablePrompts && agent.main_prompt) {
        // 检查是否是预设 ID
        const isPresetId = availablePrompts.main_prompts.some(
          (p) => p.id === agent.main_prompt,
        );
        if (isPresetId) {
          mainPromptSelect = agent.main_prompt;
          // 查找对应的预设内容用于显示
          const matchedPrompt = availablePrompts.main_prompts.find(
            (p) => p.id === agent.main_prompt,
          );
          mainPromptDisplay = matchedPrompt?.content || agent.main_prompt;
        } else {
          // 检查是否与某个预设内容匹配
          const matchedMainPrompt = availablePrompts.main_prompts.find(
            (p) => p.content === agent.main_prompt,
          );
          if (matchedMainPrompt) {
            mainPromptSelect = matchedMainPrompt.id;
          } else {
            mainPromptSelect = "custom";
          }
          // 不是预设 ID，显示存储的内容
          mainPromptDisplay = agent.main_prompt;
        }
      }

      if (availablePrompts && agent.mode_prompt) {
        // 检查是否是预设 ID
        const isPresetId = availablePrompts.mode_prompts.some(
          (p) => p.id === agent.mode_prompt,
        );
        if (isPresetId) {
          modePromptSelect = agent.mode_prompt;
          // 查找对应的预设内容用于显示
          const matchedPrompt = availablePrompts.mode_prompts.find(
            (p) => p.id === agent.mode_prompt,
          );
          modePromptDisplay = matchedPrompt?.content || agent.mode_prompt;
        } else {
          // 检查是否与某个预设内容匹配
          const matchedModePrompt = availablePrompts.mode_prompts.find(
            (p) => p.content === agent.mode_prompt,
          );
          if (matchedModePrompt) {
            modePromptSelect = matchedModePrompt.id;
          } else {
            modePromptSelect = "custom";
          }
          // 不是预设 ID，显示存储的内容
          modePromptDisplay = agent.mode_prompt;
        }
      }

      const formValues = {
        name: agent.name,
        gender: agent.gender,
        intro: agent.intro,
        opening: agent.opening,
        visibility: agent.visibility,
        main_prompt: agent.main_prompt,
        main_prompt_display: mainPromptDisplay,
        main_prompt_select: mainPromptSelect,
        personality: agent.personality,
        mode_prompt: agent.mode_prompt,
        mode_prompt_display: modePromptDisplay,
        mode_prompt_select: modePromptSelect,
        voice_id: agent.voice_id,
        score: agent.meta_data?.score,
        comment: agent.meta_data?.comment,
        tags: agent.tags || [],

        modelType: agent.llm_config ? "custom" : "default",
        // 明确设置LLM配置字段，避免字段名不匹配问题
        ...(agent.llm_config
          ? {
              // 如果 model 为空，设置一个默认值
              model: agent.llm_config.model || "gpt-4o",
              temperature: agent.llm_config.temperature || 0.7,
              max_tokens: agent.llm_config.max_tokens || 2048,
              top_p: agent.llm_config.top_p || 1,
              frequency_penalty: agent.llm_config.frequency_penalty || 0,
              presence_penalty: agent.llm_config.presence_penalty || 0,
            }
          : {}),
      };

      editForm.setFieldsValue(formValues);
    }, 100);

    setEditModalVisible(true);
  };

  // 显示详情模态框
  const showDetailModal = (agent: Agent) => {
    setCurrentAgent(agent);
    setDetailModalVisible(true);
    const nextHash = buildAgentProfilePageHash(agent.id);
    window.history.pushState(
      null,
      "",
      `${window.location.origin}${window.location.pathname}${nextHash}`,
    );
    setDeepLinkedAgentId(agent.id);
  };

  const clearAgentDetailsHash = () => {
    window.history.replaceState(
      null,
      "",
      `${window.location.origin}${window.location.pathname}#agents`,
    );
    setDeepLinkedAgentId("");
  };

  const closeDetailModal = () => {
    setDetailModalVisible(false);
    setCurrentAgent(null);
    clearAgentDetailsHash();
  };

  // 获取当前页面的智能体
  const getCurrentPageAgents = () => {
    const { current, pageSize } = pagination;
    const startIndex = (current - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return localAgents.slice(startIndex, endIndex);
  };

  // 渲染表单字段
  const renderAgentForm = (form: typeof createForm, isEdit = false) => {
    const generateRandomName = isEdit
      ? generateRandomNameForEditForm
      : generateRandomNameForForm;

    return (
      <>
        {/* 头像上传 */}
        <Form.Item label="形象">
          <Upload
            beforeUpload={isEdit ? handleEditAvatarChange : handleAvatarChange}
            showUploadList={false}
            accept="image/*"
          >
            <div
              style={{
                width: 80,
                height: 80,
                border: "1px dashed #d9d9d9",
                borderRadius: 8,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
                overflow: "hidden",
              }}
            >
              {(isEdit ? agentCopy : avatarPreview) ? (
                <AvatarDisplay
                  agent={
                    isEdit
                      ? agentCopy!
                      : ({
                          ...currentAgent,
                          avatar: avatarPreview,
                          background: avatarPreview,
                        } as Agent)
                  }
                  size={80}
                />
              ) : (
                <div style={{ textAlign: "center" }}>
                  <CameraOutlined style={{ fontSize: 20, color: "#999" }} />
                  <div style={{ marginTop: 4, fontSize: 12, color: "#999" }}>
                    上传形象图
                  </div>
                </div>
              )}
            </div>
          </Upload>
          <div style={{ marginTop: 8, fontSize: 12, color: "#666" }}>
            点击上传后可手动截取头像区域
          </div>
        </Form.Item>

        {/* 基本信息 */}
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="name"
              label="角色名称"
              rules={[
                { required: true, message: "请输入角色名称" },
                { min: 1, max: 50, message: "角色名称长度为1-50个字符" },
              ]}
            >
              <Input
                placeholder="请输入角色名称"
                suffix={
                  <Button
                    type="text"
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={generateRandomName}
                    title="随机生成英文名字"
                  />
                }
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="gender"
              label="性别"
              rules={[{ required: true, message: "请选择性别" }]}
            >
              <Radio.Group
                onChange={(e) => {
                  form.setFieldValue("voice_id", undefined);
                  if (isEdit && agentCopy) {
                    setAgentCopy({
                      ...agentCopy,
                      gender: e.target.value,
                      voice_id: undefined,
                    });
                  }
                }}
              >
                <Radio value="MALE">男</Radio>
                <Radio value="FEMALE">女</Radio>
                <Radio value="OTHER">其他</Radio>
              </Radio.Group>
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="visibility"
          label="可见性"
          rules={[{ required: true, message: "请选择可见性" }]}
        >
          <Radio.Group>
            <Radio value="PUBLIC">公开</Radio>
            <Radio value="PRIVATE">私有</Radio>
          </Radio.Group>
        </Form.Item>

        <Form.Item name="source" label="来源" initialValue="USER_CREATED">
          <Radio.Group>
            <Radio value="USER_CREATED">用户创建</Radio>
            <Radio value="AUTO_GENERATED">自动生成</Radio>
          </Radio.Group>
        </Form.Item>

        <Form.Item
          name="intro"
          label="角色简介"
          rules={[{ max: 5000, message: "角色简介长度不能超过5000个字符" }]}
        >
          <TextArea rows={3} placeholder="请输入角色简介（可选）" />
        </Form.Item>

        <Form.Item
          name="tags"
          label="标签"
          tooltip="为角色添加标签，便于分类和管理"
        >
          <Select
            mode="tags"
            style={{ width: "100%" }}
            placeholder="输入标签后按回车添加"
            tokenSeparators={[","]}
            maxTagCount={10}
            maxTagTextLength={20}
          />
        </Form.Item>

        <Form.Item
          name="opening"
          label="开场白"
          rules={[{ max: 5000, message: "开场白长度不能超过5000个字符" }]}
        >
          <TextArea rows={3} placeholder="请输入开场白（可选）" />
        </Form.Item>

        {/* 背景视频设置 */}
        <Divider>背景视频设置</Divider>

        <Form.Item label="背景视频">
          <Space direction="vertical" style={{ width: "100%" }}>
            <Upload
              beforeUpload={(file) => {
                const isVideo =
                  file.type.startsWith("video/") ||
                  file.type === "video/mp4" ||
                  file.type === "video/webm" ||
                  file.type === "video/quicktime" ||
                  file.type === "video/x-msvideo";
                if (!isVideo) {
                  message.error("只能上传视频文件（MP4、WebM、MOV等格式）!");
                  return false;
                }
                if (isEdit) {
                  // 编辑模式：直接更新 agent_copy
                  setBackgroundAnimatedFile(file);
                  const reader = new FileReader();
                  reader.onload = (e) => {
                    const videoUrl = e.target?.result as string;
                    if (agentCopy) {
                      setAgentCopy({
                        ...agentCopy,
                        background_animated: videoUrl,
                      });
                    }
                  };
                  reader.readAsDataURL(file);
                } else {
                  // 创建模式：保存文件用于后续上传
                  setBackgroundAnimatedFile(file);
                  const reader = new FileReader();
                  reader.onload = (e) => {
                    const result = e.target?.result as string;
                    setBackgroundAnimatedPreview(result);
                  };
                  reader.readAsDataURL(file);
                }
                return false;
              }}
              showUploadList={false}
              accept="video/mp4,video/webm,video/quicktime,video/x-msvideo"
            >
              <Button icon={<CameraOutlined />}>上传视频</Button>
            </Upload>
            {isEdit && currentAgent && (
              <Button
                type="dashed"
                onClick={handleOpenGenerateAnimatedModal}
                style={{ width: "100%" }}
                disabled={!currentAgent?.background}
              >
                生成背景动图
              </Button>
            )}
            {((isEdit && agentCopy?.background_animated) ||
              (!isEdit && backgroundAnimatedPreview)) && (
              <div style={{ marginTop: 8 }}>
                {(() => {
                  const previewUrl = isEdit
                    ? agentCopy?.background_animated || ""
                    : backgroundAnimatedPreview;
                  const isVideo = isVideoUrl(previewUrl);

                  if (isVideo) {
                    return (
                      <video
                        src={previewUrl}
                        controls
                        autoPlay
                        loop
                        muted
                        style={{
                          maxWidth: "100%",
                          maxHeight: "200px",
                          borderRadius: 4,
                          display: "block",
                        }}
                      />
                    );
                  } else {
                    return (
                      <img
                        src={previewUrl}
                        alt="背景动图预览"
                        style={{
                          maxWidth: "100%",
                          maxHeight: "200px",
                          borderRadius: 4,
                        }}
                      />
                    );
                  }
                })()}
                <Button
                  type="link"
                  danger
                  size="small"
                  onClick={() => {
                    if (isEdit && agentCopy) {
                      setAgentCopy({
                        ...agentCopy,
                        background_animated: undefined,
                      });
                      setBackgroundAnimatedFile(null);
                    } else {
                      setBackgroundAnimatedFile(null);
                      setBackgroundAnimatedPreview("");
                    }
                  }}
                  style={{ marginTop: 4 }}
                >
                  删除
                </Button>
              </div>
            )}
          </Space>
        </Form.Item>

        {/* 音色设置 */}
        <Divider>音色设置</Divider>

        <Form.Item
          shouldUpdate={(prev, next) => prev.gender !== next.gender}
          noStyle
        >
          {({ getFieldValue }) => (
            <Form.Item
              name="voice_id"
              label="角色音色"
              tooltip="选择角色的语音音色，用于文字转语音功能"
            >
              <VoiceSelector
                placeholder="请选择角色音色（可选）"
                imateGender={getFieldValue("gender")}
              />
            </Form.Item>
          )}
        </Form.Item>

        {/* 评分设置 */}
        <Divider>评分设置</Divider>

        <Form.Item
          name="score"
          label="角色评分"
          tooltip="对角色进行1-5分的评分，用于质量评估"
          rules={[
            {
              type: "number",
              min: 1,
              max: 5,
              message: "评分必须在1-5之间",
            },
          ]}
        >
          <ScoreSelector
            placeholder="请选择角色评分（1-5分，可选）"
            mode="star"
            showText={true}
          />
        </Form.Item>

        <Form.Item
          name="comment"
          label="备注信息"
          tooltip="对角色的备注或说明信息"
          rules={[{ max: 1000, message: "备注信息长度不能超过1000个字符" }]}
        >
          <TextArea rows={3} placeholder="请输入备注信息（可选）" />
        </Form.Item>

        {/* 提示词配置 */}
        <Divider>提示词配置</Divider>

        <Form.Item
          name="main_prompt_select"
          label="主提示词预设"
          tooltip="选择预设的主提示词，或选择自定义后在下方的文本框中编辑"
        >
          <Select
            placeholder="选择预设主提示词或自定义"
            allowClear
            onChange={(value) => {
              if (value && value !== "custom" && availablePrompts) {
                const selectedPrompt = availablePrompts.main_prompts.find(
                  (p) => p.id === value,
                );
                if (selectedPrompt) {
                  // 选择预设时，main_prompt 存储 ID，main_prompt_display 显示内容
                  form.setFieldsValue({
                    main_prompt: value, // 存储 ID
                    main_prompt_display: selectedPrompt.content || "", // 显示内容
                    main_prompt_select: value,
                  });
                }
              } else if (value === "custom") {
                // 选择自定义时，清空两个字段
                form.setFieldsValue({
                  main_prompt: "",
                  main_prompt_display: "",
                  main_prompt_select: "custom",
                });
              } else {
                form.setFieldsValue({
                  main_prompt: null,
                  main_prompt_display: null,
                  main_prompt_select: null,
                });
              }
            }}
            disabled={promptsLoading}
          >
            {availablePrompts?.main_prompts.map((prompt) => (
              <Option key={prompt.id} value={prompt.id}>
                {prompt.name}
              </Option>
            ))}
            <Option value="custom">自定义</Option>
          </Select>
        </Form.Item>

        {/* main_prompt 作为隐藏字段存储实际提交值（ID 或内容） */}
        <Form.Item name="main_prompt" hidden>
          <input type="hidden" />
        </Form.Item>

        <Form.Item
          name="main_prompt_display"
          label="主提示词"
          rules={[{ max: 50000, message: "主提示词长度不能超过50000个字符" }]}
        >
          <TextArea
            rows={5}
            placeholder="请输入主提示词（可选）"
            disabled={
              availablePrompts?.force_default_prompts === true &&
              form.getFieldValue("main_prompt_select") !== "custom" &&
              form.getFieldValue("main_prompt_select") !== null
            }
            onChange={(e) => {
              const value = e.target.value;
              const selectedId = form.getFieldValue("main_prompt_select");
              if (selectedId && selectedId !== "custom" && availablePrompts) {
                // 用户在预设模式下编辑了文本
                const selectedPrompt = availablePrompts.main_prompts.find(
                  (p) => p.id === selectedId,
                );
                if (selectedPrompt && selectedPrompt.content) {
                  if (value !== selectedPrompt.content) {
                    // 内容与预设不同，main_prompt 存储完整内容，切换为自定义
                    form.setFieldsValue({
                      main_prompt: value,
                      main_prompt_select: "custom",
                    });
                  } else {
                    // 内容与预设相同，main_prompt 保持为 ID
                    form.setFieldsValue({ main_prompt: selectedId });
                  }
                }
              } else {
                // 自定义模式，直接同步到 main_prompt
                form.setFieldsValue({ main_prompt: value });
              }
            }}
          />
        </Form.Item>

        <Form.Item
          name="personality"
          label="角色信息"
          rules={[{ max: 50000, message: "角色信息长度不能超过50000个字符" }]}
        >
          <TextArea rows={4} placeholder="请输入角色信息（可选）" />
        </Form.Item>

        <Form.Item
          name="mode_prompt_select"
          label="聊天模式预设"
          tooltip="选择预设的聊天模式提示词，或选择自定义后在下方的文本框中编辑"
        >
          <Select
            placeholder="选择预设聊天模式或自定义"
            allowClear
            onChange={(value) => {
              if (value && value !== "custom" && availablePrompts) {
                const selectedPrompt = availablePrompts.mode_prompts.find(
                  (p) => p.id === value,
                );
                if (selectedPrompt) {
                  // 选择预设时，mode_prompt 存储 ID，mode_prompt_display 显示内容
                  form.setFieldsValue({
                    mode_prompt: value, // 存储 ID
                    mode_prompt_display: selectedPrompt.content || "", // 显示内容
                    mode_prompt_select: value,
                  });
                }
              } else if (value === "custom") {
                // 选择自定义时，清空两个字段
                form.setFieldsValue({
                  mode_prompt: "",
                  mode_prompt_display: "",
                  mode_prompt_select: "custom",
                });
              } else {
                form.setFieldsValue({
                  mode_prompt: null,
                  mode_prompt_display: null,
                  mode_prompt_select: null,
                });
              }
            }}
            disabled={promptsLoading}
          >
            {availablePrompts?.mode_prompts.map((prompt) => (
              <Option key={prompt.id} value={prompt.id}>
                {prompt.name}
              </Option>
            ))}
            <Option value="custom">自定义</Option>
          </Select>
        </Form.Item>

        {/* mode_prompt 作为隐藏字段存储实际提交值（ID 或内容） */}
        <Form.Item name="mode_prompt" hidden>
          <input type="hidden" />
        </Form.Item>

        <Form.Item
          name="mode_prompt_display"
          label="聊天模式"
          rules={[{ max: 50000, message: "聊天模式长度不能超过50000个字符" }]}
        >
          <TextArea
            rows={4}
            placeholder="请输入聊天模式（可选）"
            disabled={
              availablePrompts?.force_default_prompts === true &&
              form.getFieldValue("mode_prompt_select") !== "custom" &&
              form.getFieldValue("mode_prompt_select") !== null
            }
            onChange={(e) => {
              const value = e.target.value;
              const selectedId = form.getFieldValue("mode_prompt_select");
              if (selectedId && selectedId !== "custom" && availablePrompts) {
                // 用户在预设模式下编辑了文本
                const selectedPrompt = availablePrompts.mode_prompts.find(
                  (p) => p.id === selectedId,
                );
                if (selectedPrompt && selectedPrompt.content) {
                  if (value !== selectedPrompt.content) {
                    // 内容与预设不同，mode_prompt 存储完整内容，切换为自定义
                    form.setFieldsValue({
                      mode_prompt: value,
                      mode_prompt_select: "custom",
                    });
                  } else {
                    // 内容与预设相同，mode_prompt 保持为 ID
                    form.setFieldsValue({ mode_prompt: selectedId });
                  }
                }
              } else {
                // 自定义模式，直接同步到 mode_prompt
                form.setFieldsValue({ mode_prompt: value });
              }
            }}
          />
        </Form.Item>

        {/* 模型配置 */}
        <LLMConfigForm
          models={openRouterModels}
          loading={modelsLoading}
          onRefresh={handleRefreshModels}
          onValuesChange={isEdit ? handleFormChange : undefined}
        />

        {/* 专属角色照（仅编辑模式） */}
        {isEdit && (
          <>
            <Divider>专属角色照</Divider>
            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8 }}>
                运营上传的专属角色照，每项含照片、文案、解锁所需 credit。
              </div>
              <List
                locale={{ emptyText: "暂无专属照，可点击下方按钮上传" }}
                dataSource={agentCopy?.exclusive_photos ?? []}
                renderItem={(item: ExclusivePhotoItem, index: number) => (
                  <List.Item
                    key={index}
                    actions={[
                      <Popconfirm
                        key="del"
                        title="确定删除该条？"
                        onConfirm={() => {
                          if (!agentCopy) return;
                          const next = (
                            agentCopy.exclusive_photos ?? []
                          ).filter((_, i) => i !== index);
                          setAgentCopy({
                            ...agentCopy,
                            exclusive_photos: next,
                          });
                        }}
                      >
                        <Button
                          type="text"
                          danger
                          size="small"
                          icon={<DeleteOutlined />}
                        >
                          删除
                        </Button>
                      </Popconfirm>,
                    ]}
                  >
                    <Row gutter={12} align="middle" style={{ width: "100%" }}>
                      <Col flex="80px">
                        <img
                          src={item.image_url}
                          alt=""
                          style={{
                            width: 64,
                            height: 64,
                            objectFit: "cover",
                            borderRadius: 4,
                          }}
                        />
                      </Col>
                      <Col flex="1">
                        <Input
                          placeholder="文案"
                          value={item.caption}
                          onChange={(e) => {
                            if (!agentCopy) return;
                            const next = [
                              ...(agentCopy.exclusive_photos ?? []),
                            ];
                            next[index] = {
                              ...next[index],
                              caption: e.target.value,
                            };
                            setAgentCopy({
                              ...agentCopy,
                              exclusive_photos: next,
                            });
                          }}
                          style={{ marginBottom: 6 }}
                        />
                        <InputNumber
                          min={0}
                          placeholder="解锁 credit"
                          value={item.credits_required}
                          onChange={(val) => {
                            if (!agentCopy || val == null) return;
                            const next = [
                              ...(agentCopy.exclusive_photos ?? []),
                            ];
                            next[index] = {
                              ...next[index],
                              credits_required: Number(val),
                            };
                            setAgentCopy({
                              ...agentCopy,
                              exclusive_photos: next,
                            });
                          }}
                          style={{ width: "100%" }}
                        />
                      </Col>
                    </Row>
                  </List.Item>
                )}
              />
              <Upload
                accept="image/*"
                showUploadList={false}
                beforeUpload={(file) => {
                  const isImage = file.type.startsWith("image/");
                  if (!isImage) {
                    message.error("只能上传图片");
                    return false;
                  }
                  (async () => {
                    try {
                      const res = await api.agents.uploadAvatar(file, false);
                      const url = res?.url ?? res?.data?.url;
                      if (!url || !agentCopy) return;
                      const newItem: ExclusivePhotoItem = {
                        image_url: url,
                        caption: "",
                        credits_required: 0,
                      };
                      setAgentCopy({
                        ...agentCopy,
                        exclusive_photos: [
                          ...(agentCopy.exclusive_photos ?? []),
                          newItem,
                        ],
                      });
                      message.success("已添加，请填写文案与解锁 credit");
                    } catch (err) {
                      logError("上传图片失败");
                    }
                  })();
                  return false;
                }}
              >
                <Button
                  type="dashed"
                  icon={<PlusOutlined />}
                  style={{ width: "100%" }}
                >
                  上传并添加一张专属照
                </Button>
              </Upload>
            </div>
          </>
        )}
      </>
    );
  };

  return (
    <div style={{ padding: "24px", background: "#f0f2f5", minHeight: "100vh" }}>
      {/* 操作栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col span={16}>
            <Space size="middle" wrap>
              <Search
                placeholder="搜索智能体名称或简介"
                allowClear
                style={{ width: 300 }}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                onSearch={() => loadAgents(true)}
              />
              <Select
                mode="tags"
                allowClear
                placeholder="输入或选择标签"
                style={{ minWidth: 220 }}
                value={tagFilter}
                onChange={(value: string[]) =>
                  setTagFilter(
                    value
                      .map((tag) => tag.trim())
                      .filter((tag) => tag.length > 0),
                  )
                }
                options={allTags.map((tag) => ({ label: tag, value: tag }))}
                tokenSeparators={[","]}
                maxTagCount={3}
                dropdownMatchSelectWidth={false}
              />
              <Select
                placeholder="筛选可见性"
                style={{ width: 120 }}
                value={visibilityFilter}
                onChange={(value) => setVisibilityFilter(value)}
              >
                <Option value="all">全部</Option>
                <Option value="public">公开</Option>
                <Option value="private">私有</Option>
              </Select>
              <Select
                placeholder="筛选性别"
                style={{ width: 100 }}
                value={genderFilter}
                onChange={(value) => setGenderFilter(value)}
              >
                <Option value="all">全部</Option>
                <Option value="male">男</Option>
                <Option value="female">女</Option>
                <Option value="other">其他</Option>
              </Select>
              <Select
                placeholder="筛选背景动图"
                style={{ width: 120 }}
                value={backgroundAnimatedFilter}
                onChange={(value) => setBackgroundAnimatedFilter(value)}
              >
                <Option value="all">全部</Option>
                <Option value="yes">有动图</Option>
                <Option value="no">无动图</Option>
              </Select>
              <Select
                placeholder="筛选来源"
                style={{ width: 120 }}
                value={sourceFilter}
                onChange={(value) => setSourceFilter(value)}
              >
                <Option value="all">全部</Option>
                <Option value="USER_CREATED">用户创建</Option>
                <Option value="AUTO_GENERATED">自动生成</Option>
              </Select>
              <Select
                placeholder="筛选创建者"
                style={{ width: 140 }}
                value={creatorFilter}
                onChange={(value) => setCreatorFilter(value)}
              >
                <Option value="admin">管理员创建</Option>
                <Option value="non-admin">非管理员创建</Option>
                <Option value="all">全部</Option>
              </Select>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => loadAgents(true)}
              >
                刷新
              </Button>
            </Space>
          </Col>
          <Col>
            <Space>
              <div
                style={{
                  color: "#666",
                  fontSize: "14px",
                  padding: "4px 12px",
                  backgroundColor: "#f5f5f5",
                  borderRadius: "6px",
                  border: "1px solid #d9d9d9",
                }}
              >
                共 {localAgents.length} 个角色
              </div>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setCreateModalVisible(true)}
              >
                新建智能体
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 智能体列表 */}
      <Card>
        <Spin spinning={loading}>
          {localAgents.length === 0 ? (
            <Empty description="暂无智能体数据" />
          ) : (
            <>
              <List
                grid={{
                  gutter: 16,
                  xs: 1,
                  sm: 2,
                  md: 3,
                  lg: 4,
                  xl: 4,
                  xxl: 6,
                }}
                dataSource={getCurrentPageAgents()}
                renderItem={(agent) => (
                  <List.Item>
                    <Card
                      hoverable
                      cover={
                        <div style={{ padding: 16, textAlign: "center" }}>
                          <AvatarDisplay agent={agent} size={64} />
                        </div>
                      }
                      actions={[
                        <Tooltip key="detail" title="角色详情">
                          <Button
                            type="text"
                            icon={<EyeOutlined />}
                            onClick={() => showDetailModal(agent)}
                          />
                        </Tooltip>,
                        <Tooltip key="edit" title="编辑">
                          <Button
                            type="text"
                            icon={<EditOutlined />}
                            onClick={() => showEditModal(agent)}
                          />
                        </Tooltip>,
                        <Tooltip key="avatar" title="从形象照片上截取头像">
                          <Button
                            type="text"
                            icon={<CameraOutlined />}
                            onClick={() => handleAvatarCrop(agent)}
                          />
                        </Tooltip>,
                        <Popconfirm
                          key="delete"
                          title="确定要删除这个智能体吗？"
                          onConfirm={() => handleDeleteAgent(agent)}
                          okText="确定"
                          cancelText="取消"
                        >
                          <Tooltip title="删除">
                            <Button
                              type="text"
                              danger
                              icon={<DeleteOutlined />}
                            />
                          </Tooltip>
                        </Popconfirm>,
                      ]}
                    >
                      <Card.Meta
                        title={
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 8,
                            }}
                          >
                            <span
                              style={{
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                                flex: 1,
                              }}
                            >
                              {agent.name}
                            </span>
                            <Tag
                              color={
                                agent.visibility === "PUBLIC"
                                  ? "green"
                                  : "orange"
                              }
                            >
                              {agent.visibility === "PUBLIC" ? "公开" : "私有"}
                            </Tag>
                          </div>
                        }
                        description={
                          <div>
                            <p
                              style={{
                                margin: 0,
                                color: "#666",
                                fontSize: "12px",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                display: "-webkit-box",
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: "vertical",
                                lineHeight: "1.4",
                                height: "2.8em",
                              }}
                            >
                              {agent.intro}
                            </p>
                            {agent.creator &&
                              !agent.creator.is_superuser &&
                              agent.creator.email && (
                                <div
                                  style={{
                                    marginTop: 6,
                                    fontSize: "11px",
                                    color: "#999",
                                  }}
                                >
                                  创建者: {agent.creator.email}
                                </div>
                              )}
                            <div
                              style={{
                                marginTop: 8,
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                                flexWrap: "wrap",
                              }}
                            >
                              <Tag
                                color={
                                  agent.gender === "MALE"
                                    ? "blue"
                                    : agent.gender === "FEMALE"
                                      ? "pink"
                                      : "default"
                                }
                              >
                                {agent.gender === "MALE"
                                  ? "男"
                                  : agent.gender === "FEMALE"
                                    ? "女"
                                    : "其他"}
                              </Tag>
                              {agent.source === "AUTO_GENERATED" && (
                                <Tag color="purple">自动生成</Tag>
                              )}
                              {agent.meta_data?.score && (
                                <div
                                  style={{
                                    display: "flex",
                                    alignItems: "center",
                                  }}
                                >
                                  <ScoreSelector
                                    value={agent.meta_data.score}
                                    disabled={true}
                                    mode="star"
                                    showText={false}
                                  />
                                </div>
                              )}
                              {agent.tags && agent.tags.length > 0 && (
                                <>
                                  {agent.tags.map((tag, index) => (
                                    <Tag
                                      key={index}
                                      color="geekblue"
                                      style={{ fontSize: "11px" }}
                                    >
                                      {tag}
                                    </Tag>
                                  ))}
                                </>
                              )}
                            </div>
                            {agent.meta_data?.comment && (
                              <div
                                style={{
                                  marginTop: 8,
                                  fontSize: "12px",
                                  color: "#666",
                                  backgroundColor: "#f9f9f9",
                                  padding: "4px 8px",
                                  borderRadius: "4px",
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  display: "-webkit-box",
                                  WebkitLineClamp: 2,
                                  WebkitBoxOrient: "vertical",
                                  lineHeight: "1.4",
                                  maxHeight: "2.8em",
                                }}
                              >
                                <strong>备注:</strong> {agent.meta_data.comment}
                              </div>
                            )}
                          </div>
                        }
                      />
                    </Card>
                  </List.Item>
                )}
              />

              {/* 分页 */}
              <div style={{ textAlign: "center", marginTop: 24 }}>
                <Pagination
                  current={pagination.current}
                  total={pagination.total}
                  pageSize={pagination.pageSize}
                  showSizeChanger
                  showQuickJumper
                  showTotal={(total, range) =>
                    `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
                  }
                  onChange={(page, pageSize) => {
                    setPagination({
                      current: page,
                      pageSize,
                      total: pagination.total,
                    });
                  }}
                />
              </div>
            </>
          )}
        </Spin>
      </Card>

      {/* 创建智能体模态框 */}
      <Modal
        title="新建智能体"
        open={createModalVisible}
        onOk={handleCreateAgent}
        onCancel={() => {
          setCreateModalVisible(false);
          createForm.resetFields();
          setAvatarFile(null);
          setAvatarPreview("");
          setBackgroundAnimatedFile(null);
          setBackgroundAnimatedPreview("");
        }}
        afterOpenChange={(open) => {
          if (open) {
            setCreateFormDefaults();
          }
        }}
        confirmLoading={saveLoading}
        width={800}
        destroyOnHidden
      >
        <Form form={createForm} layout="vertical" preserve={false}>
          {renderAgentForm(createForm)}
        </Form>
      </Modal>

      {/* 编辑智能体模态框 */}
      <Modal
        title="编辑智能体"
        open={editModalVisible}
        onOk={handleEditAgent}
        onCancel={() => {
          setEditModalVisible(false);
          setCurrentAgent(null);
          setAgentCopy(null);
          editForm.resetFields();
          setEditAvatarFile(null);
          setBackgroundAnimatedFile(null);
          setBackgroundAnimatedPreview("");
        }}
        confirmLoading={saveLoading}
        okButtonProps={{
          disabled: !hasChanges || saveLoading,
        }}
        width={800}
        destroyOnHidden
      >
        <Form
          form={editForm}
          layout="vertical"
          preserve={true}
          onValuesChange={handleFormChange}
        >
          {renderAgentForm(editForm, true)}
        </Form>
      </Modal>

      <AgentDetailModal
        open={detailModalVisible}
        agent={currentAgent}
        onClose={closeDetailModal}
        onEdit={(agent) => {
          setDetailModalVisible(false);
          clearAgentDetailsHash();
          showEditModal(agent);
        }}
        onDeleteBackgroundImage={handleDeleteBackgroundImage}
      />

      {/* 生成背景视频模态框 */}
      <Modal
        title="生成背景视频"
        open={generateAnimatedModalVisible}
        onOk={async () => {
          const result = await handleGenerateBackgroundAnimated();
          // 如果返回 false，不关闭模态框（错误已在函数内处理）
          if (result === false) {
            return;
          }
          // 如果返回 true 或 undefined，关闭模态框
          setGenerateAnimatedModalVisible(false);
          setGenerateAnimatedPrompt("");
          // 清理待生成操作信息
          setPendingGenerateAction(null);
        }}
        onCancel={() => {
          setGenerateAnimatedModalVisible(false);
          setGenerateAnimatedPrompt("");
          // 清理待生成操作信息
          setPendingGenerateAction(null);
        }}
        confirmLoading={generateAnimatedLoading}
        width={600}
        okButtonProps={{
          disabled: !currentAgent?.background || generateAnimatedLoading,
        }}
      >
        <Space direction="vertical" style={{ width: "100%" }} size="large">
          {!currentAgent?.background ? (
            <div style={{ color: "#ff4d4f", marginBottom: 16 }}>
              <strong>警告：</strong>请先上传背景图才能生成动图
            </div>
          ) : (
            <>
              <div>
                <div style={{ marginBottom: 8 }}>参考图：</div>
                <div
                  style={{
                    border: "1px solid #d9d9d9",
                    borderRadius: 4,
                    padding: 8,
                    textAlign: "center",
                    backgroundColor: "#fafafa",
                  }}
                >
                  <img
                    src={currentAgent.background}
                    alt="背景图预览"
                    style={{
                      maxWidth: "100%",
                      maxHeight: "200px",
                      borderRadius: 4,
                    }}
                  />
                  <div style={{ marginTop: 8, fontSize: 12, color: "#666" }}>
                    将使用此背景图作为视频生成的输入图片
                  </div>
                </div>
              </div>
              <div>
                <div style={{ marginBottom: 8 }}>视频生成提示词：</div>
                <TextArea
                  rows={4}
                  placeholder="将从背景图自动生成提示词（可编辑）"
                  value={generateAnimatedPrompt}
                  onChange={(e) => setGenerateAnimatedPrompt(e.target.value)}
                />
                <div style={{ marginTop: 4, fontSize: 12, color: "#666" }}>
                  提示：如果留空，系统将自动从背景图生成提示词
                </div>
              </div>
            </>
          )}
          <div style={{ fontSize: 12, color: "#666" }}>
            提示：系统将使用 Google Veo3 先生成 4 秒视频，然后转换为 webp
            动图格式存储
          </div>
        </Space>
      </Modal>

      {/* 修改头像截取模态框（列表中的修改头像按钮） */}
      <ImageCropModal
        visible={avatarCropModalVisible}
        imageSrc={avatarCropImageSrc}
        onCancel={handleAvatarCropCancel}
        onConfirm={handleAvatarCropConfirm}
        title="修改头像"
        existingCropData={
          currentAgentForAvatar?.extensions?.avatar_crop as
            | AvatarCropData
            | undefined
        }
      />

      {/* 创建模式头像截取模态框 */}
      <ImageCropModal
        visible={createAvatarCropModalVisible}
        imageSrc={createAvatarCropImageSrc}
        onCancel={handleCreateAvatarCropCancel}
        onConfirm={handleCreateAvatarCropConfirm}
        title="截取头像"
      />

      {/* 编辑模式头像截取模态框 */}
      <ImageCropModal
        visible={editAvatarCropModalVisible}
        imageSrc={editAvatarCropImageSrc}
        onCancel={handleEditAvatarCropCancel}
        onConfirm={handleEditAvatarCropConfirm}
        title="截取头像"
      />

      {/* 背景图裁剪模态框 */}
      <BackgroundCropModal
        visible={backgroundCropModalVisible}
        imageSrc={currentAgent?.background || ""}
        onCancel={handleBackgroundCropCancel}
        onConfirm={handleBackgroundCropConfirm}
        title="裁剪背景图为 9:16 比例"
      />
    </div>
  );
};

export default AgentManagePage;
