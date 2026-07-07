import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Card,
  Button,
  Input,
  Row,
  Col,
  message,
  Spin,
  Space,
  Modal,
  Form,
  Popconfirm,
  Empty,
  List,
  Typography,
  Image,
  Select,
  Tooltip,
  Tag,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CloseOutlined,
  DragOutlined,
} from "@ant-design/icons";
import { characterThemeApi, logError } from "../services/api";
import { useApiKeyContext } from "../hooks/useApiKey";
import { loadSelfAgentList } from "../services/agentListService";
import type {
  CharacterTheme,
  CharacterThemeCreateRequest,
  CharacterThemeUpdateRequest,
  Agent,
} from "../types";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

const { TextArea } = Input;
const { Title, Text } = Typography;
const { Option } = Select;

// 可见性显示配置
const getVisibilityConfig = (
  visibility: "PRIMARY" | "SECONDARY" | "HIDDEN",
) => {
  switch (visibility) {
    case "PRIMARY":
      return { text: "第一展示", color: "green" };
    case "SECONDARY":
      return { text: "第二展示", color: "blue" };
    case "HIDDEN":
      return { text: "不可见", color: "default" };
    default:
      return { text: "未知", color: "default" };
  }
};

interface SortableAgentItemProps {
  id: string;
  agent: Agent;
  onRemove: (agentId: string) => void;
}

const SortableAgentItem: React.FC<SortableAgentItemProps> = ({
  id,
  agent,
  onRemove,
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <List.Item
        actions={[
          <Space key="actions">
            <Tooltip title="拖拽排序">
              <Button
                type="text"
                icon={<DragOutlined />}
                {...attributes}
                {...listeners}
                style={{ cursor: "grab" }}
              />
            </Tooltip>
            <Tooltip title="移除">
              <Button
                type="text"
                danger
                icon={<CloseOutlined />}
                onClick={() => onRemove(agent.id)}
              />
            </Tooltip>
          </Space>,
        ]}
      >
        <List.Item.Meta
          avatar={
            <Image
              src={agent.avatar || ""}
              alt={agent.name}
              width={40}
              height={40}
              style={{ borderRadius: 4 }}
              fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjQwIiBoZWlnaHQ9IjQwIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTA%2BJSIgeT0iNTAlIiBmb250LXNpemU9IjE0IiBmaWxsPSIjOTk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+Tm8gSW1hZ2U8L3RleHQ+PC9zdmc+"
            />
          }
          title={agent.name}
          description={agent.intro || "无描述"}
        />
      </List.Item>
    </div>
  );
};

export const CharacterThemeManagePage: React.FC = () => {
  const { isApiKeyValid, isLoading: isApiKeyLoading } = useApiKeyContext();
  const [themes, setThemes] = useState<CharacterTheme[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [currentTheme, setCurrentTheme] = useState<CharacterTheme | null>(null);
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([]);
  const [addAgentModalVisible, setAddAgentModalVisible] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const loadAvailableAgentsRequestIdRef = useRef(0);

  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  // 拖拽传感器配置
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const loadThemes = useCallback(async () => {
    setLoading(true);
    try {
      // 管理员查看所有专区（包括隐藏的）
      const data = await characterThemeApi.list({ include_hidden: true });
      setThemes(data);
    } catch (error) {
      logError("加载专区列表失败");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAvailableAgents = useCallback(async () => {
    const requestId = ++loadAvailableAgentsRequestIdRef.current;
    const isCurrentRequest = () =>
      loadAvailableAgentsRequestIdRef.current === requestId;

    try {
      const data = await loadSelfAgentList({
        type: "public",
        shouldContinue: isCurrentRequest,
        onBatchLoaded: (accumulatedAgents) => {
          if (isCurrentRequest()) {
            setAvailableAgents(accumulatedAgents);
          }
        },
      });

      if (!isCurrentRequest()) {
        return;
      }

      setAvailableAgents(data);
    } catch (error) {
      if (isCurrentRequest()) {
        logError("加载角色列表失败");
      }
    }
  }, []);

  useEffect(() => {
    // 只在 API Key 有效时加载数据
    if (!isApiKeyLoading && isApiKeyValid) {
      loadThemes();
      loadAvailableAgents();
    }
  }, [loadThemes, loadAvailableAgents, isApiKeyValid, isApiKeyLoading]);

  useEffect(() => {
    return () => {
      loadAvailableAgentsRequestIdRef.current += 1;
    };
  }, []);

  const handleCreate = async (values: CharacterThemeCreateRequest) => {
    try {
      await characterThemeApi.create(values);
      message.success("创建专区成功");
      setCreateModalVisible(false);
      createForm.resetFields();
      loadThemes();
    } catch (error) {
      logError("创建专区失败");
    }
  };

  const handleUpdate = async (values: CharacterThemeUpdateRequest) => {
    if (!currentTheme) return;
    try {
      await characterThemeApi.update(currentTheme.id, values);
      message.success("更新专区成功");
      setEditModalVisible(false);
      editForm.resetFields();
      loadThemes();
    } catch (error) {
      logError("更新专区失败");
    }
  };

  const handleDelete = async (themeId: string) => {
    try {
      await characterThemeApi.delete(themeId);
      message.success("删除专区成功");
      loadThemes();
    } catch (error) {
      logError("删除专区失败");
    }
  };

  const handleViewDetail = async (themeId: string) => {
    try {
      const theme = await characterThemeApi.get(themeId);
      setCurrentTheme(theme);
      setDetailModalVisible(true);
    } catch (error) {
      logError("获取专区详情失败");
    }
  };

  const handleEdit = (theme: CharacterTheme) => {
    setCurrentTheme(theme);
    editForm.setFieldsValue({
      name: theme.name,
      description: theme.description,
      background_image_url: theme.background_image_url,
      visibility: theme.visibility,
    });
    setEditModalVisible(true);
  };

  const handleAddAgent = async () => {
    if (!currentTheme || !selectedAgentId) return;
    try {
      await characterThemeApi.addAgent(currentTheme.id, {
        agent_id: selectedAgentId,
      });
      message.success("添加角色成功");
      setAddAgentModalVisible(false);
      setSelectedAgentId("");
      const updatedTheme = await characterThemeApi.get(currentTheme.id);
      setCurrentTheme(updatedTheme);
    } catch (error) {
      logError("添加角色失败");
    }
  };

  const handleRemoveAgent = async (agentId: string) => {
    if (!currentTheme) return;
    try {
      await characterThemeApi.removeAgent(currentTheme.id, agentId);
      message.success("移除角色成功");
      const updatedTheme = await characterThemeApi.get(currentTheme.id);
      setCurrentTheme(updatedTheme);
    } catch (error) {
      logError("移除角色失败");
    }
  };

  const agentsInTheme = currentTheme?.agents.map((item) => item.agent_id) || [];
  const availableAgentsForAdd = availableAgents.filter(
    (agent) => !agentsInTheme.includes(agent.id),
  );

  return (
    <div style={{ padding: "24px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "24px",
        }}
      >
        <Title level={2}>角色主题专区管理</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateModalVisible(true)}
        >
          创建专区
        </Button>
      </div>

      <Spin spinning={loading}>
        {themes.length === 0 ? (
          <Empty description="暂无专区" />
        ) : (
          <Row gutter={[16, 16]}>
            {themes.map((theme) => (
              <Col key={theme.id} xs={24} sm={12} md={8} lg={6}>
                <Card
                  hoverable
                  cover={
                    theme.background_image_url ? (
                      <Image
                        src={theme.background_image_url}
                        alt={theme.name}
                        height={150}
                        style={{ objectFit: "cover" }}
                        fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgZmlsbD0iI2RkZCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjE0IiBmaWxsPSIjOTk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+Tm8gSW1hZ2U8L3RleHQ+PC9zdmc+"
                      />
                    ) : (
                      <div
                        style={{
                          height: 150,
                          background:
                            "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "white",
                        }}
                      >
                        {theme.name}
                      </div>
                    )
                  }
                  actions={[
                    <Tooltip key="view" title="查看详情">
                      <EyeOutlined onClick={() => handleViewDetail(theme.id)} />
                    </Tooltip>,
                    <Tooltip key="edit" title="编辑">
                      <EditOutlined onClick={() => handleEdit(theme)} />
                    </Tooltip>,
                    <Popconfirm
                      key="delete"
                      title="确定要删除这个专区吗？"
                      onConfirm={() => handleDelete(theme.id)}
                      okText="确定"
                      cancelText="取消"
                    >
                      <DeleteOutlined />
                    </Popconfirm>,
                  ]}
                >
                  <Card.Meta
                    title={
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "flex-start",
                          gap: 8,
                          whiteSpace: "normal",
                        }}
                      >
                        <span
                          style={{
                            whiteSpace: "normal",
                            wordBreak: "break-word",
                            lineHeight: 1.4,
                          }}
                        >
                          {theme.name}
                        </span>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                            flexWrap: "wrap",
                            whiteSpace: "normal",
                          }}
                        >
                          <Text type="secondary" style={{ fontSize: 13 }}>
                            可见性:
                          </Text>
                          <Tag
                            color={getVisibilityConfig(theme.visibility).color}
                          >
                            {getVisibilityConfig(theme.visibility).text}
                          </Tag>
                        </div>
                      </div>
                    }
                    description={
                      <div>
                        <Text type="secondary" ellipsis>
                          {theme.description || "无描述"}
                        </Text>
                        <div style={{ marginTop: 8 }}>
                          <Text type="secondary">
                            角色数量: {theme.agents.length}
                          </Text>
                        </div>
                      </div>
                    }
                  />
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>

      {/* 创建专区模态框 */}
      <Modal
        title="创建专区"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          createForm.resetFields();
        }}
        onOk={() => createForm.submit()}
      >
        <Form form={createForm} onFinish={handleCreate} layout="vertical">
          <Form.Item
            name="name"
            label="专区名称"
            rules={[{ required: true, message: "请输入专区名称" }]}
          >
            <Input placeholder="例如：圣诞主题专区" />
          </Form.Item>
          <Form.Item name="description" label="专区描述">
            <TextArea rows={4} placeholder="请输入专区描述" />
          </Form.Item>
          <Form.Item name="background_image_url" label="背景图URL">
            <Input placeholder="请输入背景图URL地址" />
          </Form.Item>
          <Form.Item
            name="visibility"
            label="可见性"
            initialValue="HIDDEN"
            tooltip="第一展示和第二展示只能各有一个专区，设置时会自动将其他专区的相同可见性改为不可见"
          >
            <Select placeholder="请选择可见性">
              <Option value="PRIMARY">第一展示</Option>
              <Option value="SECONDARY">第二展示</Option>
              <Option value="HIDDEN">不可见</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑专区模态框 */}
      <Modal
        title="编辑专区"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          editForm.resetFields();
        }}
        onOk={() => editForm.submit()}
      >
        <Form form={editForm} onFinish={handleUpdate} layout="vertical">
          <Form.Item
            name="name"
            label="专区名称"
            rules={[{ required: true, message: "请输入专区名称" }]}
          >
            <Input placeholder="例如：圣诞主题专区" />
          </Form.Item>
          <Form.Item name="description" label="专区描述">
            <TextArea rows={4} placeholder="请输入专区描述" />
          </Form.Item>
          <Form.Item name="background_image_url" label="背景图URL">
            <Input placeholder="请输入背景图URL地址" />
          </Form.Item>
          <Form.Item
            name="visibility"
            label="可见性"
            tooltip="第一展示和第二展示只能各有一个专区，设置时会自动将其他专区的相同可见性改为不可见"
          >
            <Select placeholder="请选择可见性">
              <Option value="PRIMARY">第一展示</Option>
              <Option value="SECONDARY">第二展示</Option>
              <Option value="HIDDEN">不可见</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 专区详情模态框 */}
      <Modal
        title={currentTheme?.name || "专区详情"}
        open={detailModalVisible}
        onCancel={() => {
          setDetailModalVisible(false);
          setCurrentTheme(null);
        }}
        footer={[
          <Button
            key="add"
            type="primary"
            onClick={() => setAddAgentModalVisible(true)}
          >
            添加角色
          </Button>,
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {currentTheme && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>可见性：</Text>
              <Tag
                color={getVisibilityConfig(currentTheme.visibility).color}
                style={{ marginLeft: 8 }}
              >
                {getVisibilityConfig(currentTheme.visibility).text}
              </Tag>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>描述：</Text>
              <Text>{currentTheme.description || "无描述"}</Text>
            </div>
            {currentTheme.background_image_url && (
              <div style={{ marginBottom: 16 }}>
                <Image
                  src={currentTheme.background_image_url}
                  alt={currentTheme.name}
                  width="100%"
                  style={{ maxHeight: 200, objectFit: "cover" }}
                />
              </div>
            )}
            <Title level={4}>
              角色列表（拖拽左侧图标或使用上下箭头调整顺序）
            </Title>
            {currentTheme.agents.length === 0 ? (
              <Empty description="暂无角色" />
            ) : (
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={async (event: DragEndEvent) => {
                  const { active, over } = event;
                  if (!over || active.id === over.id || !currentTheme) return;

                  const oldIndex = currentTheme.agents.findIndex(
                    (item) => item.agent_id === active.id,
                  );
                  const newIndex = currentTheme.agents.findIndex(
                    (item) => item.agent_id === over.id,
                  );

                  if (oldIndex === -1 || newIndex === -1) return;

                  const newAgents = arrayMove(
                    currentTheme.agents,
                    oldIndex,
                    newIndex,
                  );
                  const newAgentIds = newAgents.map((item) => item.agent_id);

                  try {
                    await characterThemeApi.reorderAgents(currentTheme.id, {
                      agent_ids: newAgentIds,
                    });
                    message.success("调整顺序成功");
                    const updatedTheme = await characterThemeApi.get(
                      currentTheme.id,
                    );
                    setCurrentTheme(updatedTheme);
                  } catch (error) {
                    logError("调整顺序失败");
                  }
                }}
              >
                <SortableContext
                  items={currentTheme.agents.map((item) => item.agent_id)}
                  strategy={verticalListSortingStrategy}
                >
                  <List
                    dataSource={currentTheme.agents}
                    renderItem={(item, _index) => {
                      const agent =
                        item.agent ||
                        availableAgents.find((a) => a.id === item.agent_id);
                      if (!agent) return null;
                      return (
                        <SortableAgentItem
                          key={item.agent_id}
                          id={item.agent_id}
                          agent={agent}
                          onRemove={handleRemoveAgent}
                        />
                      );
                    }}
                  />
                </SortableContext>
              </DndContext>
            )}
          </div>
        )}
      </Modal>

      {/* 添加角色模态框 */}
      <Modal
        title="添加角色"
        open={addAgentModalVisible}
        onCancel={() => {
          setAddAgentModalVisible(false);
          setSelectedAgentId("");
        }}
        onOk={handleAddAgent}
        okButtonProps={{ disabled: !selectedAgentId }}
      >
        <Select
          style={{ width: "100%" }}
          placeholder="请选择要添加的角色（支持搜索名称和描述）"
          value={selectedAgentId}
          onChange={setSelectedAgentId}
          showSearch
          filterOption={(input, option): boolean => {
            const agent = availableAgentsForAdd.find(
              (a) => a.id === option?.value,
            );
            if (!agent) return false;
            const searchText = input.toLowerCase();
            const nameMatch = agent.name.toLowerCase().includes(searchText);
            const introMatch =
              agent.intro !== undefined &&
              agent.intro !== null &&
              agent.intro.toLowerCase().includes(searchText);
            const descriptionMatch =
              agent.description !== undefined &&
              agent.description !== null &&
              agent.description.toLowerCase().includes(searchText);
            return nameMatch || introMatch || descriptionMatch;
          }}
        >
          {availableAgentsForAdd.map((agent) => (
            <Option key={agent.id} value={agent.id}>
              {agent.name}
            </Option>
          ))}
        </Select>
      </Modal>
    </div>
  );
};

export default CharacterThemeManagePage;
