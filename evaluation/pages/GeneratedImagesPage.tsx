/**
 * CREATED_BY_AGENT
 *
 * 生成图片管理页面
 * 用于查看每个角色所有聊天生成的图片
 */

import React, { useState, useEffect, useCallback } from "react";
import {
  Card,
  Row,
  Col,
  List,
  Empty,
  Spin,
  Input,
  Image,
  Modal,
  Typography,
  Tag,
  Space,
  Button,
  message,
  Tooltip,
  Avatar,
  Badge,
  Divider,
} from "antd";
import {
  PictureOutlined,
  ReloadOutlined,
  SearchOutlined,
  UserOutlined,
  ClockCircleOutlined,
  ExpandOutlined,
} from "@ant-design/icons";
import { agentApi, generatedImagesApi } from "../services/api";
import type { Agent, GeneratedImage } from "../types";

const { Text, Paragraph, Title } = Typography;
const { Search } = Input;

const GeneratedImagesPage: React.FC = () => {
  // 状态
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [images, setImages] = useState<GeneratedImage[]>([]);
  const [imageCounts, setImageCounts] = useState<Record<string, number>>({});
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [loadingImages, setLoadingImages] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [previewImage, setPreviewImage] = useState<GeneratedImage | null>(null);

  // 加载角色列表和图片数量
  const loadAgents = useCallback(async () => {
    setLoadingAgents(true);
    try {
      const [agentsData, countsData] = await Promise.all([
        agentApi.list({ limit: 200 }),
        generatedImagesApi.getImageCounts(),
      ]);
      setAgents(agentsData);
      setImageCounts(countsData.counts);
    } catch (error) {
      message.error("加载角色列表失败");
      console.error("加载角色列表失败:", error);
    } finally {
      setLoadingAgents(false);
    }
  }, []);

  // 加载角色的生成图片
  const loadImages = useCallback(async (agentId: string) => {
    setLoadingImages(true);
    try {
      const data = await generatedImagesApi.getAgentImages(agentId, {
        limit: 100,
      });
      setImages(data.images);
    } catch (error) {
      message.error("加载图片失败");
      console.error("加载图片失败:", error);
      setImages([]);
    } finally {
      setLoadingImages(false);
    }
  }, []);

  // 初始加载
  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  // 选择角色时加载图片
  useEffect(() => {
    if (selectedAgent) {
      loadImages(selectedAgent.id);
    } else {
      setImages([]);
    }
  }, [selectedAgent, loadImages]);

  // 过滤角色列表
  const filteredAgents = agents.filter((agent) =>
    agent.name.toLowerCase().includes(searchText.toLowerCase()),
  );

  // 按用户分组图片
  const groupedImages = React.useMemo(() => {
    const groups: Record<
      string,
      {
        user_id: string;
        user_nickname: string | null;
        images: GeneratedImage[];
      }
    > = {};
    for (const image of images) {
      const userId = image.user_id || "unknown";
      if (!groups[userId]) {
        groups[userId] = {
          user_id: userId,
          user_nickname: image.user_nickname,
          images: [],
        };
      }
      groups[userId].images.push(image);
    }
    return Object.values(groups);
  }, [images]);

  // 格式化日期
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "未知";
    const date = new Date(dateStr);
    return date.toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div style={{ padding: "24px", height: "100%", overflow: "hidden" }}>
      <Row gutter={24} style={{ height: "100%" }}>
        {/* 左侧：角色列表 */}
        <Col span={6} style={{ height: "100%", overflow: "hidden" }}>
          <Card
            title={
              <Space>
                <UserOutlined />
                <span>角色列表</span>
                <Tag color="blue">{agents.length}</Tag>
              </Space>
            }
            extra={
              <Button
                icon={<ReloadOutlined />}
                onClick={loadAgents}
                loading={loadingAgents}
                size="small"
              />
            }
            style={{ height: "100%", display: "flex", flexDirection: "column" }}
            bodyStyle={{
              flex: 1,
              overflow: "hidden",
              padding: "12px",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <Search
              placeholder="搜索角色..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ marginBottom: 12 }}
              allowClear
            />
            <div style={{ flex: 1, overflow: "auto" }}>
              {loadingAgents ? (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "center",
                    padding: 40,
                  }}
                >
                  <Spin />
                </div>
              ) : filteredAgents.length === 0 ? (
                <Empty description="没有找到角色" />
              ) : (
                <List
                  dataSource={filteredAgents}
                  renderItem={(agent) => (
                    <List.Item
                      onClick={() => setSelectedAgent(agent)}
                      style={{
                        cursor: "pointer",
                        padding: "8px 12px",
                        borderRadius: 8,
                        backgroundColor:
                          selectedAgent?.id === agent.id
                            ? "#e6f4ff"
                            : "transparent",
                        marginBottom: 4,
                        border:
                          selectedAgent?.id === agent.id
                            ? "1px solid #91caff"
                            : "1px solid transparent",
                        transition: "all 0.2s",
                      }}
                    >
                      <List.Item.Meta
                        avatar={
                          <Avatar
                            src={agent.avatar}
                            icon={<UserOutlined />}
                            size={40}
                          />
                        }
                        title={
                          <Text
                            strong={selectedAgent?.id === agent.id}
                            style={{ fontSize: 14 }}
                          >
                            {agent.name}
                          </Text>
                        }
                        description={
                          <Space size={4}>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {agent.visibility === "PUBLIC" ? "公开" : "私有"}
                            </Text>
                            {imageCounts[agent.id] > 0 && (
                              <Badge
                                count={imageCounts[agent.id]}
                                style={{ backgroundColor: "#52c41a" }}
                                size="small"
                              />
                            )}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              )}
            </div>
          </Card>
        </Col>

        {/* 右侧：图片网格 */}
        <Col span={18} style={{ height: "100%", overflow: "hidden" }}>
          <Card
            title={
              selectedAgent ? (
                <Space>
                  <PictureOutlined />
                  <span>{selectedAgent.name} 的生成图片</span>
                  <Tag color="green">{images.length} 张</Tag>
                </Space>
              ) : (
                <Space>
                  <PictureOutlined />
                  <span>生成图片</span>
                </Space>
              )
            }
            extra={
              selectedAgent && (
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => loadImages(selectedAgent.id)}
                  loading={loadingImages}
                  size="small"
                >
                  刷新
                </Button>
              )
            }
            style={{ height: "100%", display: "flex", flexDirection: "column" }}
            bodyStyle={{ flex: 1, overflow: "auto", padding: "16px" }}
          >
            {!selectedAgent ? (
              <Empty
                description="请从左侧选择一个角色查看生成图片"
                style={{ marginTop: 100 }}
              />
            ) : loadingImages ? (
              <div
                style={{
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  height: "100%",
                }}
              >
                <Spin size="large" />
              </div>
            ) : images.length === 0 ? (
              <Empty
                description="该角色暂无生成图片"
                style={{ marginTop: 100 }}
              />
            ) : (
              <div>
                {groupedImages.map((group, groupIndex) => (
                  <div key={group.user_id} style={{ marginBottom: 24 }}>
                    {/* 用户分组标题 */}
                    <Divider orientation="left" style={{ margin: "16px 0" }}>
                      <Space>
                        <UserOutlined />
                        <Text strong>{group.user_nickname || "未知用户"}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          ({group.user_id.slice(0, 16)}...)
                        </Text>
                        <Tag color="blue">{group.images.length} 张</Tag>
                      </Space>
                    </Divider>
                    {/* 该用户的图片 */}
                    <Row gutter={[16, 16]}>
                      {group.images.map((image, index) => (
                        <Col
                          key={`${groupIndex}-${index}`}
                          xs={12}
                          sm={8}
                          md={6}
                          lg={4}
                        >
                          <Card
                            hoverable
                            size="small"
                            cover={
                              <div
                                style={{
                                  position: "relative",
                                  paddingTop: "100%",
                                  overflow: "hidden",
                                }}
                              >
                                <img
                                  src={image.url}
                                  alt={`生成图片 ${index + 1}`}
                                  style={{
                                    position: "absolute",
                                    top: 0,
                                    left: 0,
                                    width: "100%",
                                    height: "100%",
                                    objectFit: "cover",
                                  }}
                                  onClick={() => setPreviewImage(image)}
                                />
                                <div
                                  style={{
                                    position: "absolute",
                                    top: 8,
                                    right: 8,
                                  }}
                                >
                                  <Tooltip title="查看大图">
                                    <Button
                                      type="primary"
                                      shape="circle"
                                      size="small"
                                      icon={<ExpandOutlined />}
                                      onClick={() => setPreviewImage(image)}
                                    />
                                  </Tooltip>
                                </div>
                              </div>
                            }
                            bodyStyle={{ padding: "8px" }}
                          >
                            <Tooltip title={image.generation_prompt}>
                              <Paragraph
                                ellipsis={{ rows: 2 }}
                                style={{ fontSize: 12, marginBottom: 4 }}
                              >
                                {image.generation_prompt}
                              </Paragraph>
                            </Tooltip>
                            <Text type="secondary" style={{ fontSize: 10 }}>
                              <ClockCircleOutlined style={{ marginRight: 4 }} />
                              {formatDate(image.created_at)}
                            </Text>
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 图片预览弹窗 */}
      <Modal
        open={!!previewImage}
        onCancel={() => setPreviewImage(null)}
        footer={null}
        width={800}
        centered
        title={
          <Space>
            <PictureOutlined />
            <span>图片详情</span>
          </Space>
        }
      >
        {previewImage && (
          <div>
            <div style={{ textAlign: "center", marginBottom: 16 }}>
              <Image
                src={previewImage.url}
                alt="生成图片"
                style={{ maxHeight: 500, objectFit: "contain" }}
              />
            </div>
            <Card size="small" style={{ marginTop: 16 }}>
              <Title level={5} style={{ marginBottom: 12 }}>
                生成提示词
              </Title>
              <Paragraph
                style={{
                  backgroundColor: "#f5f5f5",
                  padding: 12,
                  borderRadius: 8,
                  marginBottom: 12,
                }}
              >
                {previewImage.generation_prompt}
              </Paragraph>
              <Space split={<span style={{ color: "#d9d9d9" }}>|</span>}>
                {previewImage.width && previewImage.height && (
                  <Text type="secondary">
                    尺寸: {previewImage.width} x {previewImage.height}
                  </Text>
                )}
                <Text type="secondary">
                  生成时间: {formatDate(previewImage.created_at)}
                </Text>
                {previewImage.user_id && (
                  <Text type="secondary">
                    用户ID: {previewImage.user_id.slice(0, 8)}...
                  </Text>
                )}
              </Space>
            </Card>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default GeneratedImagesPage;
