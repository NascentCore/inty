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
  RobotOutlined,
  CameraOutlined,
  ReloadOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import type { UploadProps } from "antd";
import api, { logError } from "../services/api";
import modelCacheService from "../services/modelCache";
import type { Agent, AgentCreateRequest, OpenRouterModel } from "../types";
import LLMConfigForm from "../components/common/LLMConfigForm";

const { TextArea } = Input;
const { Search } = Input;
const { Option } = Select;

// 类型已在 types.ts 中定义

export const AgentManagePage: React.FC = () => {
  // 状态管理
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);
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

      setLoading(true);
      try {
        const response = await api.agents.list({
          limit: 100, // 先获取所有数据，前端分页
        });

        let filteredAgents = response || [];

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

        setAgents(filteredAgents);
        setPagination((prev) => ({
          ...prev,
          total: filteredAgents.length,
        }));
      } catch (error) {
        console.error("加载智能体列表失败:", error);
        message.error("加载智能体列表失败");
      } finally {
        setLoading(false);
      }
    },
    [searchText, visibilityFilter, genderFilter],
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

  useEffect(() => {
    loadAgents();
    loadModels(); // 加载模型列表
  }, [loadAgents, loadModels]);

  // 处理头像上传
  const handleAvatarChange: UploadProps["beforeUpload"] = (file) => {
    const isImage = file.type.startsWith("image/");
    if (!isImage) {
      message.error("只能上传图片文件!");
      return false;
    }

    setAvatarFile(file);
    const reader = new FileReader();
    reader.onload = (e) => {
      setAvatarPreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
    return false;
  };

  // 处理编辑头像上传
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

  // 创建智能体
  const handleCreateAgent = async () => {
    try {
      // 在表单验证前添加调试日志
      console.log("=== 创建智能体 - 表单验证前 ===");
      console.log("表单所有字段值:", createForm.getFieldsValue());
      console.log("modelType:", createForm.getFieldValue("modelType"));
      console.log("model:", createForm.getFieldValue("model"));
      console.log("temperature:", createForm.getFieldValue("temperature"));
      console.log("max_tokens:", createForm.getFieldValue("max_tokens"));

      const values = await createForm.validateFields();

      // 表单验证通过后的日志
      console.log("=== 创建智能体 - 表单验证通过 ===");
      console.log("验证后的所有值:", values);
      console.log("验证后的 modelType:", values.modelType);
      console.log("验证后的 model:", values.model);

      setSaveLoading(true);

      let avatarUrl = "";
      let backgroundUrl = "";
      let backgroundImages: string[] = [];

      // 如果有头像文件，先上传
      if (avatarFile) {
        try {
          const uploadResult = await api.agents.uploadAvatar(avatarFile);
          avatarUrl = uploadResult.avatar_url || uploadResult.data?.avatar_url;
          backgroundUrl = uploadResult.url || uploadResult.data?.url;
          if (backgroundUrl) {
            backgroundImages = [backgroundUrl];
          }
          console.log(
            `上传成功：头像：${avatarUrl} 背景：${backgroundUrl} 背景图: ${backgroundImages.join(", ")}`,
          );
        } catch (uploadError) {
          logError("头像上传失败:", uploadError);
          return;
        }
      }

      const agentData: AgentCreateRequest = {
        ...values,
        avatar: avatarUrl,
        background: backgroundUrl,
        background_images: backgroundImages,
      };

      // Display background images on the page as notification
      console.log(
        `创建成功：头像：${avatarUrl} 背景：${backgroundUrl} 背景图: ${backgroundImages.join(", ")}`,
      );

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

      await api.agents.create(agentData);
      message.success("智能体创建成功");
      setCreateModalVisible(false);
      createForm.resetFields();
      setAvatarFile(null);
      setAvatarPreview("");
      loadAgents(true);
    } catch (error) {
      console.error("=== 创建智能体 - 表单验证失败 ===");
      console.error("错误详情:", error);
      console.error("错误字段:", error.errorFields);
      console.error("错误值:", error.values);
      console.error("当前表单状态:", createForm.getFieldsValue());
      message.error("创建智能体失败，请重试");
    } finally {
      setSaveLoading(false);
    }
  };

  // 编辑智能体
  const handleEditAgent = async () => {
    if (!currentAgent) return;

    try {
      // 在表单验证前添加调试日志
      console.log("=== 编辑智能体 - 表单验证前 ===");
      console.log("当前智能体:", currentAgent);
      console.log("表单所有字段值:", editForm.getFieldsValue());
      console.log("modelType:", editForm.getFieldValue("modelType"));
      console.log("model:", editForm.getFieldValue("model"));
      console.log("temperature:", editForm.getFieldValue("temperature"));
      console.log("max_tokens:", editForm.getFieldValue("max_tokens"));



      const values = await editForm.validateFields();

      // 表单验证通过后的日志
      console.log("=== 编辑智能体 - 表单验证通过 ===");
      console.log("验证后的所有值:", values);
      console.log("验证后的 modelType:", values.modelType);
      console.log("验证后的 model:", values.model);

      setSaveLoading(true);

      let avatarUrl = currentAgent.avatar;
      let backgroundUrl = currentAgent.background;
      let backgroundImages = currentAgent.background_images || [];

      // 如果有新头像文件，先上传
      if (editAvatarFile) {
        try {
          const uploadResult = await api.agents.uploadAvatar(editAvatarFile);
          avatarUrl = uploadResult.avatar_url || uploadResult.data?.avatar_url;
          backgroundUrl = uploadResult.url || uploadResult.data?.url;
          if (backgroundUrl) {
            backgroundImages = [backgroundUrl];
          }
        } catch (uploadError) {
          logError(`头像上传失败，请重试，错误信息：${uploadError.message}`);
          return;
        }
      }

      const updateData = {
        ...values,
        avatar: avatarUrl,
        background: backgroundUrl,
        background_images: backgroundImages,
      };

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

      console.log("=== 发送到后端的更新数据 ===");
      console.log("智能体ID:", currentAgent.id);
      console.log("更新数据:", updateData);
      console.log("LLM配置:", updateData.llm_config);

      const updateResponse = await api.agents.update(currentAgent.id, updateData);

      console.log("=== 后端更新响应 ===");
      console.log("响应数据:", updateResponse);
      message.success("智能体更新成功");
      setEditModalVisible(false);
      setCurrentAgent(null);
      editForm.resetFields();
      setEditAvatarFile(null);
      setEditAvatarPreview("");
      loadAgents();
    } catch (error) {
      console.error("=== 编辑智能体 - 表单验证失败 ===");
      console.error("错误详情:", error);
      console.error("错误字段:", error.errorFields);
      console.error("错误值:", error.values);
      console.error("当前表单状态:", editForm.getFieldsValue());
      message.error("更新智能体失败，请重试");
    } finally {
      setSaveLoading(false);
    }
  };

  // 删除智能体
  const handleDeleteAgent = async (agent: Agent) => {
    try {
      await api.agents.delete(agent.id);
      message.success("智能体删除成功");
      loadAgents();
    } catch (error) {
      console.error("删除智能体失败:", error);
      message.error("删除智能体失败，请重试");
    }
  };

  // 显示编辑模态框
  const showEditModal = (agent: Agent) => {
    setCurrentAgent(agent);
    setEditAvatarPreview(agent.avatar || "");

    // 添加调试日志
    console.log("=== showEditModal - 智能体数据 ===");
    console.log("智能体:", agent);
    console.log("llm_config:", agent.llm_config);
    console.log("llm_config.model:", agent.llm_config?.model);
    console.log("modelType 将设置为:", agent.llm_config ? "custom" : "default");
    if (agent.llm_config) {
      console.log("LLM配置字段:", {
        model: agent.llm_config.model,
        temperature: agent.llm_config.temperature,
        max_tokens: agent.llm_config.max_tokens,
        top_p: agent.llm_config.top_p,
        frequency_penalty: agent.llm_config.frequency_penalty,
        presence_penalty: agent.llm_config.presence_penalty,
      });
      console.log("model 字段是否为空:", !agent.llm_config.model);
      console.log("model 字段类型:", typeof agent.llm_config.model);
    }

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

      console.log("=== showEditModal - 设置表单值 ===");
      console.log("要设置的表单值:", formValues);

      editForm.setFieldsValue(formValues);

      // 设置后立即检查表单值
      setTimeout(() => {
        console.log("=== showEditModal - 设置表单值后 ===");
        console.log("表单当前值:", editForm.getFieldsValue());
        console.log("modelType:", editForm.getFieldValue("modelType"));
        console.log("model:", editForm.getFieldValue("model"));
      }, 50);
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
    return agents.slice(startIndex, endIndex);
  };

  // 渲染表单字段
  const renderAgentForm = (form: any, isEdit = false) => (
    <>
      {/* 头像上传 */}
      <Form.Item label="形像">
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
              <img
                src={isEdit ? editAvatarPreview : avatarPreview}
                alt="avatar"
                style={{ width: "100%", height: "100%", objectFit: "contain" }}
              />
            ) : (
              <div style={{ textAlign: "center" }}>
                <CameraOutlined style={{ fontSize: 20, color: "#999" }} />
                <div style={{ marginTop: 4, fontSize: 12, color: "#999" }}>
                  上传形像图
                </div>
              </div>
            )}
          </div>
        </Upload>
        <div style={{ marginTop: 8, fontSize: 12, color: "#666" }}>
          上传头像后，系统会自动设置背景图为原图，头像为裁剪后的版本
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
            <Input placeholder="请输入角色名称" />
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
          { required: true, message: "请输入角色简介" },
          { min: 1, max: 5000, message: "角色简介长度为1-5000个字符" },
        ]}
      >
        <TextArea rows={3} placeholder="请输入角色简介" />
      </Form.Item>

      <Form.Item
        name="opening"
        label="开场白"
        rules={[
          { required: true, message: "请输入开场白" },
          { min: 1, max: 5000, message: "开场白长度为1-5000个字符" },
        ]}
      >
        <TextArea rows={3} placeholder="请输入开场白" />
      </Form.Item>

      {/* 提示词配置 */}
      <Divider>提示词配置</Divider>

      <Form.Item
        name="main_prompt"
        label="主提示词"
        rules={[
          { required: true, message: "请输入主提示词" },
          { min: 1, max: 50000, message: "主提示词长度为1-50000个字符" },
        ]}
      >
        <TextArea rows={5} placeholder="请输入主提示词" />
      </Form.Item>

      <Form.Item
        name="personality"
        label="角色信息"
        rules={[
          { required: true, message: "请输入角色信息" },
          { min: 1, max: 50000, message: "角色信息长度为1-50000个字符" },
        ]}
      >
        <TextArea rows={4} placeholder="请输入角色信息" />
      </Form.Item>

      <Form.Item
        name="mode_prompt"
        label="聊天模式"
        rules={[
          { required: true, message: "请输入聊天模式" },
          { min: 1, max: 50000, message: "聊天模式长度为1-50000个字符" },
        ]}
      >
        <TextArea rows={4} placeholder="请输入聊天模式" />
      </Form.Item>

      {/* 模型配置 */}
      <LLMConfigForm
        models={openRouterModels}
        loading={modelsLoading}
        onRefresh={handleRefreshModels}
      />
    </>
  );

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
          {agents.length === 0 ? (
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
                          <Avatar
                            size={64}
                            src={agent.avatar}
                            icon={<RobotOutlined />}
                          />
                        </div>
                      }
                      actions={[
                        <Tooltip title="角色详情">
                          <Button
                            type="text"
                            icon={<EyeOutlined />}
                            onClick={() => showDetailModal(agent)}
                          />
                        </Tooltip>,
                        <Tooltip title="编辑">
                          <Button
                            type="text"
                            icon={<EditOutlined />}
                            onClick={() => showEditModal(agent)}
                          />
                        </Tooltip>,
                        <Popconfirm
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
                              size="small"
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
                                size="small"
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
          <div style={{ maxHeight: 600, overflowY: "auto", padding: 16 }}>
            <Card size="small" title="基本信息" style={{ marginBottom: 16 }}>
              <Row gutter={[16, 16]} align="middle">
                <Col span={6} style={{ textAlign: "center" }}>
                  <Avatar
                    size={80}
                    src={currentAgent.avatar}
                    icon={<RobotOutlined />}
                  />
                  <div style={{ marginTop: 8 }}>
                    <Tag
                      color={
                        currentAgent.visibility === "PUBLIC"
                          ? "green"
                          : "orange"
                      }
                    >
                      {currentAgent.visibility === "PUBLIC" ? "公开" : "私有"}
                    </Tag>
                  </div>
                </Col>
                <Col span={18}>
                  <p>
                    <strong>ID:</strong> {currentAgent.id}
                  </p>
                  <p>
                    <strong>名称:</strong> {currentAgent.name}
                  </p>
                  <p>
                    <strong>性别:</strong>{" "}
                    {currentAgent.gender === "MALE"
                      ? "男"
                      : currentAgent.gender === "FEMALE"
                        ? "女"
                        : "其他"}
                  </p>
                  <p>
                    <strong>简介:</strong> {currentAgent.intro || "无"}
                  </p>
                  <p>
                    <strong>开场白:</strong> {currentAgent.opening || "无"}
                  </p>
                  <p>
                    <strong>描述:</strong> {currentAgent.description || "无"}
                  </p>
                  <p>
                    <strong>创建时间:</strong>{" "}
                    {currentAgent.created_at
                      ? new Date(currentAgent.created_at).toLocaleString()
                      : "无"}
                  </p>
                  <p>
                    <strong>更新时间:</strong>{" "}
                    {currentAgent.updated_at
                      ? new Date(currentAgent.updated_at).toLocaleString()
                      : "无"}
                  </p>
                </Col>
              </Row>
            </Card>

            <Card size="small" title="提示词配置" style={{ marginBottom: 16 }}>
              <p>
                <strong>主提示词:</strong>
              </p>
              <div
                style={{
                  background: "#f5f5f5",
                  padding: 12,
                  borderRadius: 6,
                  maxHeight: 200,
                  overflowY: "auto",
                  whiteSpace: "pre-wrap",
                  fontSize: "12px",
                }}
              >
                {currentAgent.main_prompt || "无"}
              </div>
              <p style={{ marginTop: 16 }}>
                <strong>角色信息:</strong>
              </p>
              <div
                style={{
                  background: "#f5f5f5",
                  padding: 12,
                  borderRadius: 6,
                  maxHeight: 200,
                  overflowY: "auto",
                  whiteSpace: "pre-wrap",
                  fontSize: "12px",
                }}
              >
                {currentAgent.personality || "无"}
              </div>
              <p style={{ marginTop: 16 }}>
                <strong>聊天模式:</strong>
              </p>
              <div
                style={{
                  background: "#f5f5f5",
                  padding: 12,
                  borderRadius: 6,
                  maxHeight: 200,
                  overflowY: "auto",
                  whiteSpace: "pre-wrap",
                  fontSize: "12px",
                }}
              >
                {currentAgent.mode_prompt || "无"}
              </div>
            </Card>

            <Card size="small" title="图片资源" style={{ marginBottom: 16 }}>
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <p>
                    <strong>头像:</strong>
                  </p>
                  {currentAgent.avatar ? (
                    <img
                      src={currentAgent.avatar}
                      alt="avatar"
                      style={{
                        width: "100%",
                        maxWidth: 120,
                        height: "auto",
                        borderRadius: 8,
                      }}
                    />
                  ) : (
                    <span style={{ color: "#999" }}>无</span>
                  )}
                </Col>
                <Col span={12}>
                  <p>
                    <strong>背景图:</strong>
                  </p>
                  {currentAgent.background ? (
                    <img
                      src={currentAgent.background}
                      alt="background"
                      style={{
                        width: "100%",
                        maxWidth: 120,
                        height: "auto",
                        borderRadius: 8,
                      }}
                    />
                  ) : (
                    <span style={{ color: "#999" }}>无</span>
                  )}
                </Col>
              </Row>
              {currentAgent.background_images &&
                currentAgent.background_images.length > 0 && (
                  <>
                    <p style={{ marginTop: 16 }}>
                      <strong>背景图列表:</strong>
                    </p>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {currentAgent.background_images.map((img, index) => (
                        <img
                          key={index}
                          src={img}
                          alt={`background-${index}`}
                          style={{
                            width: 80,
                            height: 80,
                            objectFit: "cover",
                            borderRadius: 6,
                          }}
                        />
                      ))}
                    </div>
                  </>
                )}
            </Card>

            {currentAgent.llm_config && (
              <Card size="small" title="自定义模型配置">
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <p>
                      <strong>模型:</strong>{" "}
                      {currentAgent.llm_config.model || "无"}
                    </p>
                    <p>
                      <strong>温度:</strong>{" "}
                      {currentAgent.llm_config.temperature ?? "无"}
                    </p>
                    <p>
                      <strong>最大令牌数:</strong>{" "}
                      {currentAgent.llm_config.max_tokens ?? "无"}
                    </p>
                  </Col>
                  <Col span={12}>
                    <p>
                      <strong>Top P:</strong>{" "}
                      {currentAgent.llm_config.top_p ?? "无"}
                    </p>
                    <p>
                      <strong>频率惩罚:</strong>{" "}
                      {currentAgent.llm_config.frequency_penalty ?? "无"}
                    </p>
                    <p>
                      <strong>存在惩罚:</strong>{" "}
                      {currentAgent.llm_config.presence_penalty ?? "无"}
                    </p>
                  </Col>
                </Row>
              </Card>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default AgentManagePage;
