import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Card,
  Button,
  Input,
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
  OpenRouterModel,
  AvatarCropData,
} from "../types";
import LLMConfigForm from "../components/common/LLMConfigForm";
import VoiceSelector from "../components/common/VoiceSelector";
import ScoreSelector from "../components/common/ScoreSelector";
import { useAgents } from "../hooks/useAgents";
import AgentInfoDisplay from "../components/common/AgentInfoDisplay";
import { generateRandomName } from "../utils/nameGenerator";
import { hasAgentChanged } from "../utils/agentComparison";
import ImageCropModal from "../components/common/ImageCropModal";
import AvatarDisplay from "../components/common/AvatarDisplay";

const { TextArea } = Input;
const { Search } = Input;
const { Option } = Select;

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

  // 修改头像弹窗状态
  const [avatarCropModalVisible, setAvatarCropModalVisible] = useState(false);
  const [avatarCropImageSrc, setAvatarCropImageSrc] = useState<string>("");
  const [currentAgentForAvatar, setCurrentAgentForAvatar] =
    useState<Agent | null>(null);

  // 模型相关状态
  const [openRouterModels, setOpenRouterModels] = useState<OpenRouterModel[]>(
    [],
  );
  const [modelsLoading, setModelsLoading] = useState(false);

  // 背景视频相关状态
  const [backgroundAnimatedFile, setBackgroundAnimatedFile] =
    useState<File | null>(null);
  const [backgroundAnimatedPreview, setBackgroundAnimatedPreview] =
    useState<string>("");
  const [generateAnimatedModalVisible, setGenerateAnimatedModalVisible] =
    useState(false);
  const [generateAnimatedLoading, setGenerateAnimatedLoading] = useState(false);
  const [generateAnimatedPrompt, setGenerateAnimatedPrompt] = useState("");

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
    async (reset = false) => {
      if (reset) {
        setPagination((prev) => ({ ...prev, current: 1 }));
      }

      // 使用 useAgents hook 的 loadAgents
      await loadAgentsFromHook(true);
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
        const nameMatch = agent.name
          ?.toLowerCase()
          .includes(normalizedSearchText);
        const introMatch = agent.intro
          ? agent.intro.toLowerCase().includes(normalizedSearchText)
          : false;
        return nameMatch || introMatch;
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

    setLocalAgents(filteredAgents);
    setPagination((prev) => ({
      ...prev,
      total: filteredAgents.length,
    }));
  }, [agents, searchText, visibilityFilter, genderFilter, tagFilter]);

  useEffect(() => {
    loadAgents();
    loadModels(); // 加载模型列表
  }, [loadAgents, loadModels]);

  // 处理头像上传（创建模式，不截取）
  const handleAvatarChange: UploadProps["beforeUpload"] = (file) => {
    const isImage = file.type.startsWith("image/");
    if (!isImage) {
      message.error("只能上传图片文件!");
      return false;
    }

    setAvatarFile(file);
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      setAvatarPreview(result);
    };
    reader.readAsDataURL(file);
    return false;
  };

  // 处理编辑头像上传（编辑模式，直接上传）
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

      // 更新 agent_copy：清空 avatar 和 avatar_crop，设置 background 为新图片
      if (agentCopy) {
        setAgentCopy({
          ...agentCopy,
          avatar: undefined, // 清空 avatar
          background: imageUrl, // 设置 background 为新图片
          extensions: {
            ...agentCopy.extensions,
            avatar_crop: undefined, // 清空 avatar_crop
          },
        });
      }
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

  // 处理头像截取确认
  const handleAvatarCropConfirm = async (cropData: AvatarCropData) => {
    if (!currentAgentForAvatar) return;

    try {
      // 更新智能体头像坐标信息
      const updateData = {
        extensions: {
          avatar_crop: cropData,
        },
      };

      const updatedAgent = (await api
        .getIntyClient()
        .api.v1.ai.agents.update(
          currentAgentForAvatar.id,
          updateData,
        )) as unknown as Agent;
      if (updatedAgent) {
        message.success("头像坐标设置成功");
        // 刷新智能体列表
        loadAgents();
      } else {
        message.error("头像坐标设置失败");
      }
    } catch (error) {
      logError("设置头像坐标失败");
      console.error("设置头像坐标失败:", error);
      message.error("设置头像坐标失败，请重试");
    } finally {
      // 关闭弹窗并重置状态
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

  // 处理生成背景视频
  const handleGenerateBackgroundAnimated = async () => {
    console.log("handleGenerateBackgroundAnimated 被调用", {
      currentAgent: currentAgent?.id,
      hasBackground: !!currentAgent?.background,
      prompt: generateAnimatedPrompt,
    });

    if (!currentAgent) {
      console.warn("currentAgent 为空");
      message.warning("请先选择要编辑的角色");
      return false; // 阻止 Modal 关闭
    }

    // 验证背景图是否存在
    if (!currentAgent.background) {
      console.warn("背景图为空");
      message.warning("请先上传背景图");
      return false; // 阻止 Modal 关闭
    }

    try {
      setGenerateAnimatedLoading(true);
      console.log("开始调用 API", {
        agentId: currentAgent.id,
        prompt: generateAnimatedPrompt.trim() || undefined,
      });

      // prompt 可以为空，后端会自动生成
      const updatedAgent = await api.agents.generateBackgroundAnimated(
        currentAgent.id,
        generateAnimatedPrompt.trim() || undefined,
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
        message.success("背景视频生成成功");
        setGenerateAnimatedModalVisible(false);
        setGenerateAnimatedPrompt("");
        return true; // 允许 Modal 关闭
      } else {
        message.error("背景视频生成失败");
        return false; // 阻止 Modal 关闭
      }
    } catch (error) {
      console.error("生成背景视频失败:", error);
      message.error(
        `生成背景视频失败: ${
          error instanceof Error ? error.message : "未知错误"
        }`,
      );
      return false; // 阻止 Modal 关闭
    } finally {
      setGenerateAnimatedLoading(false);
    }
  };

  // 创建智能体
  const handleCreateAgent = async () => {
    try {
      const values = await createForm.validateFields();

      setSaveLoading(true);

      // 从 values 中排除 score 和 comment，因为它们需要放到 meta_data 中
      const { score, comment, ...otherValues } = values;

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
      if (avatarFile) {
        agentData.avatar = avatarFile;
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
      const newAgent = await createAgentFromHook(agentData);

      if (newAgent) {
        // 成功创建，关闭弹窗并重置状态
        setCreateModalVisible(false);
        createForm.resetFields();
        setAvatarFile(null);
        setAvatarPreview("");
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

      // 从 values 中排除 score 和 comment，因为它们需要放到 meta_data 中
      const { score, comment, ...otherValues } = values;

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
      const success = await deleteAgentFromHook(agent.id);
      if (success) {
        // 删除成功后，重新加载列表以确保数据同步
        loadAgents();
      }
    } catch (error) {
      console.error("删除智能体失败:", error);
      message.error("删除智能体失败，请重试");
    }
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
    });

    // 预填表单 - 使用 setTimeout 确保 Modal 完全渲染后再设置表单值
    setTimeout(() => {
      const formValues = {
        name: agent.name,
        gender: agent.gender,
        intro: agent.intro,
        opening: agent.opening,
        visibility: agent.visibility,
        main_prompt: agent.main_prompt,
        personality: agent.personality,
        mode_prompt: agent.mode_prompt,
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
            头像将在后端从上传的形象图片截取
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
              <Radio.Group>
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
                onClick={() => {
                  if (!currentAgent?.background) {
                    message.warning("请先上传背景图");
                    return;
                  }
                  setGenerateAnimatedModalVisible(true);
                  setGenerateAnimatedPrompt("");
                }}
                style={{ width: "100%" }}
                disabled={!currentAgent?.background}
              >
                生成背景视频
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
                        alt="背景视频预览"
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
          name="voice_id"
          label="角色音色"
          tooltip="选择角色的语音音色，用于文字转语音功能"
        >
          <VoiceSelector placeholder="请选择角色音色（可选）" />
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
          name="main_prompt"
          label="主提示词"
          rules={[{ max: 50000, message: "主提示词长度不能超过50000个字符" }]}
        >
          <TextArea rows={5} placeholder="请输入主提示词（可选）" />
        </Form.Item>

        <Form.Item
          name="personality"
          label="角色信息"
          rules={[{ max: 50000, message: "角色信息长度不能超过50000个字符" }]}
        >
          <TextArea rows={4} placeholder="请输入角色信息（可选）" />
        </Form.Item>

        <Form.Item
          name="mode_prompt"
          label="聊天模式"
          rules={[{ max: 50000, message: "聊天模式长度不能超过50000个字符" }]}
        >
          <TextArea rows={4} placeholder="请输入聊天模式（可选）" />
        </Form.Item>

        {/* 模型配置 */}
        <LLMConfigForm
          models={openRouterModels}
          loading={modelsLoading}
          onRefresh={handleRefreshModels}
          onValuesChange={isEdit ? handleFormChange : undefined}
        />
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
                    value.map((tag) => tag.trim()).filter((tag) => tag.length > 0),
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
              <Button icon={<ReloadOutlined />} onClick={() => loadAgents(true)}>
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
                        <Tooltip key="avatar" title="修改头像">
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
                                  {agent.tags.slice(0, 2).map((tag, index) => (
                                    <Tag
                                      key={index}
                                      color="geekblue"
                                      style={{ fontSize: "11px" }}
                                    >
                                      {tag}
                                    </Tag>
                                  ))}
                                  {agent.tags.length > 2 && (
                                    <Tag
                                      color="default"
                                      style={{ fontSize: "11px" }}
                                    >
                                      +{agent.tags.length - 2}
                                    </Tag>
                                  )}
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

      {/* 智能体详情模态框 */}
      <Modal
        title="角色详情"
        open={detailModalVisible}
        onCancel={() => {
          setDetailModalVisible(false);
          setCurrentAgent(null);
        }}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
          <Button
            key="edit"
            type="primary"
            onClick={() => {
              setDetailModalVisible(false);
              if (currentAgent) showEditModal(currentAgent);
            }}
          >
            编辑
          </Button>,
        ]}
        width={800}
      >
        {currentAgent && <AgentInfoDisplay agent={currentAgent} />}
      </Modal>

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
        }}
        onCancel={() => {
          setGenerateAnimatedModalVisible(false);
          setGenerateAnimatedPrompt("");
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
            提示：将使用 Google Veo3 生成 4 秒视频，直接存储视频地址
          </div>
        </Space>
      </Modal>

      {/* 修改头像截取模态框 */}
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
    </div>
  );
};

export default AgentManagePage;
