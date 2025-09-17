import React, { useState, useEffect, useCallback } from "react";
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
  Avatar,
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
import type { Agent, AgentCreateRequest, OpenRouterModel, AvatarCropData } from "../types";
import LLMConfigForm from "../components/common/LLMConfigForm";
import VoiceSelector from "../components/common/VoiceSelector";
import { useAgents } from "../hooks/useAgents";
import AgentInfoDisplay from "../components/common/AgentInfoDisplay";
import { generateRandomName } from "../utils/nameGenerator";
import ImageCropModal from "../components/common/ImageCropModal";
import AvatarDisplay from "../components/common/AvatarDisplay";

const { TextArea } = Input;
const { Search } = Input;
const { Option } = Select;

// 类型已在 types.ts 中定义

export const AgentManagePage: React.FC = () => {
  // 使用 useAgents hook
  const { agents, loading, loadAgents: loadAgentsFromHook, deleteAgent: deleteAgentFromHook } = useAgents({
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
  const [editAvatarPreview, setEditAvatarPreview] = useState<string>("");


  // 修改头像弹窗状态
  const [avatarCropModalVisible, setAvatarCropModalVisible] = useState(false);
  const [avatarCropImageSrc, setAvatarCropImageSrc] = useState<string>("");
  const [currentAgentForAvatar, setCurrentAgentForAvatar] = useState<Agent | null>(null);


  // 模型相关状态
  const [openRouterModels, setOpenRouterModels] = useState<OpenRouterModel[]>(
    [],
  );
  const [modelsLoading, setModelsLoading] = useState(false);

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

  // 监听 agents 变化，应用筛选
  useEffect(() => {
    let filteredAgents = agents || [];

    // 搜索筛选
    if (searchText) {
      filteredAgents = filteredAgents.filter(
        (agent) =>
          agent.name.toLowerCase().includes(searchText.toLowerCase()) ||
          agent.intro?.toLowerCase().includes(searchText.toLowerCase()),
      );
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

    setLocalAgents(filteredAgents);
    setPagination((prev) => ({
      ...prev,
      total: filteredAgents.length,
    }));
  }, [agents, searchText, visibilityFilter, genderFilter]);

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
      setEditAvatarPreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
    return false;
  };



  // 处理修改头像截取
  const handleAvatarCrop = (agent: Agent) => {
    // 检查是否有背景图
    if (!agent.background_images || agent.background_images.length === 0) {
      message.warning("该角色没有背景图，无法修改头像");
      return;
    }

    // 使用第一张背景图作为截取源头
    const backgroundImage = agent.background_images[0];
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
          avatar_crop: cropData
        }
      };

      const updatedAgent = await api.inty.api.v1.ai.agents.update(currentAgentForAvatar.id, updateData) as unknown as Agent;
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

  // 创建智能体
  const handleCreateAgent = async () => {
    try {
      const values = await createForm.validateFields();

      setSaveLoading(true);

      let avatarUrl = "";
      let backgroundUrl = "";
      let backgroundImages: string[] = [];

      // 如果有头像文件，先上传（创建模式，不截取）
      if (avatarFile) {
        try {
          const uploadResult = await api.inty.api.v1.uploadImage({ file: avatarFile, cropping_avatar: true }); // Enable cropping for avatar
          const data = uploadResult.data as Record<string, unknown>;
          avatarUrl = (data?.avatar_url as string) || (data?.url as string);
          backgroundUrl = data?.url as string;
          if (backgroundUrl) {
            backgroundImages = [backgroundUrl];
          }

        } catch (uploadError) {
          const errorMessage = uploadError instanceof Error ? uploadError.message : String(uploadError);
          logError(`头像上传失败，请重试，错误信息：${errorMessage}`);
          return;
        }
      }

      const agentData: AgentCreateRequest = {
        ...values,
        avatar: avatarUrl,
        background: backgroundUrl,
        background_images: backgroundImages,
        voice_id: values.voice_id,
      };

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

      await api.inty.api.v1.ai.agents.create(agentData);
      message.success("智能体创建成功");
      setCreateModalVisible(false);
      createForm.resetFields();
      setAvatarFile(null);
      setAvatarPreview("");
      loadAgents(true);
    } catch (error) {

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

      let avatarUrl = currentAgent.avatar;
      let backgroundUrl = currentAgent.background;
      let backgroundImages = currentAgent.background_images || [];

      // 如果有新头像文件，先上传
      if (editAvatarFile) {
        try {
          const uploadResult = await api.inty.api.v1.uploadImage({ file: editAvatarFile, cropping_avatar: true }); // Enable cropping for avatar
          const data = uploadResult.data as Record<string, unknown>;
          avatarUrl = (data?.avatar_url as string) || (data?.url as string);
          backgroundUrl = data?.url as string;
          if (backgroundUrl) {
            backgroundImages = [backgroundUrl];
          }
        } catch (uploadError) {
          const errorMessage = uploadError instanceof Error ? uploadError.message : String(uploadError);
          logError(`头像上传失败，请重试，错误信息：${errorMessage}`);
          return;
        }
      }

      const updateData = {
        ...values,
        avatar: avatarUrl,
        background: backgroundUrl,
        background_images: backgroundImages,
        voice_id: values.voice_id,
      };

      // 如果有新头像文件，清理旧的avatar_crop数据，让组件使用新的avatar字段
      if (editAvatarFile) {
        updateData.extensions = {
          ...currentAgent.extensions,
          avatar_crop: null, // 清理旧的截取数据
        };
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

      await api.inty.api.v1.ai.agents.update(currentAgent.id, updateData);
      message.success("智能体更新成功");
      setEditModalVisible(false);
      setCurrentAgent(null);
      editForm.resetFields();
      setEditAvatarFile(null);
      setEditAvatarPreview("");
      loadAgents();
    } catch (error) {

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
      const randomName = generateRandomName(gender as 'MALE' | 'FEMALE' | 'OTHER');
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
    const currentGender = createForm.getFieldValue('gender') || 'FEMALE';
    const randomName = generateRandomName(currentGender as 'MALE' | 'FEMALE' | 'OTHER');
    createForm.setFieldValue('name', randomName);
  };

  // 随机生成角色名字（编辑表单）
  const generateRandomNameForEditForm = () => {
    const currentGender = editForm.getFieldValue('gender') || 'FEMALE';
    const randomName = generateRandomName(currentGender as 'MALE' | 'FEMALE' | 'OTHER');
    editForm.setFieldValue('name', randomName);
  };

  // 显示编辑模态框
  const showEditModal = (agent: Agent) => {
    setCurrentAgent(agent);
    setEditAvatarPreview(agent.avatar || "");

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
    const generateRandomName = isEdit ? generateRandomNameForEditForm : generateRandomNameForForm;

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
            {(isEdit ? editAvatarPreview : avatarPreview) ? (
                <Avatar
                  size={80}
                src={isEdit ? editAvatarPreview : avatarPreview}
                  icon={<CameraOutlined />}
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
        rules={[
          { max: 5000, message: "角色简介长度不能超过5000个字符" },
        ]}
      >
        <TextArea rows={3} placeholder="请输入角色简介（可选）" />
      </Form.Item>

      <Form.Item
        name="opening"
        label="开场白"
        rules={[
          { max: 5000, message: "开场白长度不能超过5000个字符" },
        ]}
      >
        <TextArea rows={3} placeholder="请输入开场白（可选）" />
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

      {/* 提示词配置 */}
      <Divider>提示词配置</Divider>

      <Form.Item
        name="main_prompt"
        label="主提示词"
        rules={[
          { max: 50000, message: "主提示词长度不能超过50000个字符" },
        ]}
      >
        <TextArea rows={5} placeholder="请输入主提示词（可选）" />
      </Form.Item>

      <Form.Item
        name="personality"
        label="角色信息"
        rules={[
          { max: 50000, message: "角色信息长度不能超过50000个字符" },
        ]}
      >
        <TextArea rows={4} placeholder="请输入角色信息（可选）" />
      </Form.Item>

      <Form.Item
        name="mode_prompt"
        label="聊天模式"
        rules={[
          { max: 50000, message: "聊天模式长度不能超过50000个字符" },
        ]}
      >
        <TextArea rows={4} placeholder="请输入聊天模式（可选）" />
      </Form.Item>

      {/* 模型配置 */}
      <LLMConfigForm
        models={openRouterModels}
        loading={modelsLoading}
        onRefresh={handleRefreshModels}
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
            <Space size="middle">
              <Search
                placeholder="搜索智能体名称或简介"
                allowClear
                style={{ width: 300 }}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                onSearch={() => loadAgents(true)}
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
              <Button
                icon={<ReloadOutlined />}
                onClick={() => loadAgents(true)}
              >
                刷新
              </Button>
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalVisible(true)}
            >
              新建智能体
            </Button>
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
                          <AvatarDisplay
                            agent={agent}
                            size={64}
                          />
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
                            <div style={{ marginTop: 8 }}>
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
                            </div>
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
          editForm.resetFields();
          setEditAvatarFile(null);
          setEditAvatarPreview("");
        }}
        confirmLoading={saveLoading}
        width={800}
        destroyOnHidden
      >
        <Form form={editForm} layout="vertical" preserve={true}>
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
        {currentAgent && (
          <AgentInfoDisplay agent={currentAgent} />
        )}
      </Modal>


      {/* 修改头像截取模态框 */}
      <ImageCropModal
        visible={avatarCropModalVisible}
        imageSrc={avatarCropImageSrc}
        onCancel={handleAvatarCropCancel}
        onConfirm={handleAvatarCropConfirm}
        title="修改头像"
        existingCropData={currentAgentForAvatar?.extensions?.avatar_crop as AvatarCropData | undefined}
      />
    </div>
  );
};

export default AgentManagePage;
