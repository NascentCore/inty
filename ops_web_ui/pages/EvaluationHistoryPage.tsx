/**
 * 评测记录页面 - 查看历史评测会话和结果
 */

import React, { useState, useEffect, useCallback } from "react";
import {
  Layout,
  Card,
  Table,
  Button,
  Tag,
  Space,
  Typography,
  Row,
  Col,
  Statistic,
  Input,
  Select,
  DatePicker,
  message,
  Modal,
  Tooltip,
  Badge,
  Progress,
} from "antd";
import {
  EyeOutlined,
  DownloadOutlined,
  SearchOutlined,
  FilterOutlined,
  HistoryOutlined,
  RobotOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import type { Dayjs } from "dayjs";
import api from "../services/api";
import { MultiAgentChatDisplay } from "../components/evaluation/MultiAgentChatDisplay";
import { JsonDisplayModal } from "../components/common/JsonDisplayModal";
import { useJsonDisplay } from "../hooks/useJsonDisplay";
import type { EvaluationSession, EvaluationResult } from "../types";
import { formatUtcTimeRaw } from "../utils/dateUtils";

const { Content } = Layout;
const { Text } = Typography;
const { Search } = Input;
const { Option } = Select;
const { RangePicker } = DatePicker;

interface EvaluationSessionWithStats extends EvaluationSession {
  total_tests?: number;
  completed_tests?: number;
  average_score?: number;
  best_score?: number;
  worst_score?: number;
  agent_count?: number;
}

interface EvaluationHistoryPageProps {
  onNavigateToEvaluation?: () => void;
}

export const EvaluationHistoryPage: React.FC<EvaluationHistoryPageProps> = ({
  onNavigateToEvaluation,
}) => {
  // 状态管理
  const [sessions, setSessions] = useState<EvaluationSessionWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSession, setSelectedSession] =
    useState<EvaluationSession | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [sessionResults, setSessionResults] = useState<EvaluationResult[]>([]);
  const [resultsLoading, setResultsLoading] = useState(false);

  // 批量操作状态
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [batchLoading, setBatchLoading] = useState(false);

  // 筛选和搜索状态
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [dateRange, setDateRange] = useState<
    [Dayjs | null, Dayjs | null] | null
  >(null);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });
  const { current: currentPage, pageSize } = pagination;

  // JSON显示功能
  const { jsonModalVisible, jsonData, showJson, hideJson } = useJsonDisplay();

  // 加载评测会话列表
  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);

      const params: {
        skip: number;
        limit: number;
        status?: string;
        search?: string;
        start_date?: string;
        end_date?: string;
      } = {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
      };

      if (statusFilter) {
        params.status = statusFilter;
      }

      if (searchText) {
        params.search = searchText;
      }

      if (dateRange) {
        params.start_date = dateRange[0]?.format("YYYY-MM-DD");
        params.end_date = dateRange[1]?.format("YYYY-MM-DD");
      }

      const response = await api.sessions.list(params);
      const sessionsData = Array.isArray(response)
        ? response
        : (response as { items?: EvaluationSession[] }).items || [];

      // 为每个会话加载统计信息
      const sessionsWithStats = await Promise.all(
        sessionsData.map(async (session: EvaluationSession) => {
          try {
            const results = await api.sessions.getResults(session.id);
            const scores = results
              .filter((r: EvaluationResult) => r.overall_score != null)
              .map((r: EvaluationResult) => r.overall_score!);

            const totalTests =
              (session.selected_agents?.length || 0) *
              (session.questions?.length ||
                session.config?.questions?.length ||
                0);
            return {
              ...session,
              best_score: scores.length > 0 ? Math.max(...scores) : undefined,
              worst_score: scores.length > 0 ? Math.min(...scores) : undefined,
              agent_count: session.selected_agents?.length || 0,
              total_tests: totalTests,
              completed_tests: results.length,
              average_score:
                scores.length > 0
                  ? scores.reduce((a, b) => a + b, 0) / scores.length
                  : undefined,
            } as EvaluationSessionWithStats;
          } catch (error) {
            console.error(`加载会话 ${session.id} 统计信息失败:`, error);
            const totalTests =
              (session.selected_agents?.length || 0) *
              (session.questions?.length ||
                session.config?.questions?.length ||
                0);
            return {
              ...session,
              agent_count: session.selected_agents?.length || 0,
              total_tests: totalTests,
              completed_tests: 0,
            } as EvaluationSessionWithStats;
          }
        }),
      );

      setSessions(sessionsWithStats);

      // 更新分页信息
      if (Array.isArray(response)) {
        setPagination((prev) => ({ ...prev, total: response.length }));
      } else if ((response as { total?: number }).total !== undefined) {
        setPagination((prev) => ({
          ...prev,
          total: (response as { total: number }).total,
        }));
      }
    } catch (error) {
      console.error("加载评测会话失败:", error);
      message.error("加载评测会话失败");
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, statusFilter, searchText, dateRange]);

  // 初始加载
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // 查看详情
  const handleViewDetail = async (session: EvaluationSession) => {
    setSelectedSession(session);
    setDetailModalVisible(true);
    setResultsLoading(true);

    try {
      const results = await api.sessions.getResults(session.id);
      setSessionResults(results);
    } catch (error) {
      console.error("加载会话结果失败:", error);
      message.error("加载对话记录失败");
      setSessionResults([]);
    } finally {
      setResultsLoading(false);
    }
  };

  // 查看JSON
  const handleShowJson = async (session: EvaluationSession) => {
    try {
      const results = await api.sessions.getResults(session.id);
      const exportData = {
        session: session,
        results: results,
      };
      showJson(exportData);
    } catch (error) {
      console.error("加载会话结果失败:", error);
      message.error("加载会话结果失败");
    }
  };

  // 继续评测
  const handleContinueEvaluation = () => {
    // TODO: 实现跳转到评测页面并加载指定会话
    if (onNavigateToEvaluation) {
      onNavigateToEvaluation();
    }
    message.info("跳转到评测页面功能开发中");
  };

  // 创建新评测
  const handleCreateNew = () => {
    if (onNavigateToEvaluation) {
      onNavigateToEvaluation();
    }
  };

  // 导出结果
  const handleExport = async (sessionId: string) => {
    try {
      // 获取会话信息和结果
      const session = sessions.find((s) => s.id === sessionId);
      if (!session) {
        message.error("会话不存在");
        return;
      }

      const results = await api.sessions.getResults(sessionId);

      // 直接导出原始数据，保持完整结构
      const exportData = {
        session: session,
        results: results,
        export_metadata: {
          export_time: new Date().toISOString(),
          total_results: results.length,
        },
      };

      // 生成文件名
      const timestamp = new Date()
        .toISOString()
        .slice(0, 19)
        .replace(/:/g, "-");
      const filename = `evaluation_${session.name}_${timestamp}.json`;

      // 创建JSON blob
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: "application/json",
      });

      // 创建并下载文件
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      message.success(`评测结果已导出: ${filename}`);
    } catch (error) {
      console.error("导出失败:", error);
      message.error("导出失败，请重试");
    }
  };

  // 批量删除
  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning("请先选择要删除的评测会话");
      return;
    }

    Modal.confirm({
      title: "批量删除确认",
      content: `确定要删除选中的 ${selectedRowKeys.length} 个评测会话吗？此操作不可恢复。`,
      okText: "确定删除",
      cancelText: "取消",
      okType: "danger",
      onOk: async () => {
        setBatchLoading(true);
        try {
          // 并行删除所有选中的会话
          await Promise.all(
            selectedRowKeys.map((sessionId) => api.sessions.delete(sessionId)),
          );
          message.success(`成功删除 ${selectedRowKeys.length} 个评测会话`);
          setSelectedRowKeys([]);
          loadSessions();
        } catch (error) {
          message.error("批量删除失败");
        } finally {
          setBatchLoading(false);
        }
      },
    });
  };

  // 批量导出
  const handleBatchExport = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning("请先选择要导出的评测会话");
      return;
    }

    setBatchLoading(true);
    try {
      // TODO: 实现批量导出功能
      message.info(`批量导出 ${selectedRowKeys.length} 个会话的功能开发中`);
    } catch (error) {
      message.error("批量导出失败");
    } finally {
      setBatchLoading(false);
    }
  };

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusConfig = {
      pending: {
        color: "default",
        icon: <ClockCircleOutlined />,
        text: "等待中",
      },
      running: {
        color: "processing",
        icon: <ClockCircleOutlined />,
        text: "运行中",
      },
      completed: {
        color: "success",
        icon: <CheckCircleOutlined />,
        text: "已完成",
      },
      failed: {
        color: "error",
        icon: <ExclamationCircleOutlined />,
        text: "失败",
      },
      cancelled: { color: "warning", icon: <StopOutlined />, text: "已取消" },
    };

    const config =
      statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;

    return (
      <Tag color={config.color} icon={config.icon}>
        {config.text}
      </Tag>
    );
  };

  // 表格列定义
  const columns: ColumnsType<EvaluationSessionWithStats> = [
    {
      title: "评测名称",
      dataIndex: "name",
      key: "name",
      width: 200,
      render: (text, record) => (
        <div>
          <Text strong>{text}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: "12px" }}>
            ID: {record.id.slice(0, 8)}...
          </Text>
        </div>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 120,
      render: (status) => getStatusTag(status),
      filters: [
        { text: "等待中", value: "pending" },
        { text: "运行中", value: "running" },
        { text: "已完成", value: "completed" },
        { text: "失败", value: "failed" },
        { text: "已取消", value: "cancelled" },
      ],
    },
    {
      title: "进度",
      key: "progress",
      width: 150,
      render: (text, record) => {
        const total =
          (record.total_tests ??
            (record.agent_count || 0) *
              (record.questions?.length ||
                record.config?.questions?.length ||
                0)) ||
          0;
        const completed =
          (record.completed_tests ?? record.results?.length) || 0;
        const percentage =
          total > 0 ? Math.round((completed / total) * 100) : 0;

        return (
          <div>
            <Progress
              percent={percentage}
              size="small"
              status={record.status === "failed" ? "exception" : "normal"}
              showInfo={false}
            />
            <Text style={{ fontSize: "12px" }}>
              {completed}/{total}
            </Text>
          </div>
        );
      },
    },
    {
      title: "智能体",
      dataIndex: "agent_count",
      key: "agent_count",
      width: 100,
      render: (count) => (
        <Badge count={count} style={{ backgroundColor: "#1890ff" }}>
          <RobotOutlined style={{ fontSize: "16px" }} />
        </Badge>
      ),
    },
    {
      title: "问题数",
      dataIndex: "questions",
      key: "questions",
      width: 100,
      render: (questions) => questions?.length || 0,
    },
    {
      title: "评分范围",
      key: "score_range",
      width: 120,
      render: (text, record) => {
        if (record.best_score == null || record.worst_score == null) {
          return <Text type="secondary">-</Text>;
        }

        return (
          <div>
            <Text strong style={{ color: "#52c41a" }}>
              {record.best_score.toFixed(1)}
            </Text>
            <Text type="secondary"> - </Text>
            <Text strong style={{ color: "#faad14" }}>
              {record.worst_score.toFixed(1)}
            </Text>
          </div>
        );
      },
    },
    {
      title: "平均分",
      dataIndex: "average_score",
      key: "average_score",
      width: 100,
      render: (score) => {
        if (score == null) return <Text type="secondary">-</Text>;

        return (
          <Text
            strong
            style={{
              color:
                score >= 7 ? "#52c41a" : score >= 5 ? "#faad14" : "#ff4d4f",
            }}
          >
            {score.toFixed(1)}
          </Text>
        );
      },
      sorter: (a, b) => (a.average_score || 0) - (b.average_score || 0),
    },
    {
      title: "创建时间 (UTC)",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (time) => formatUtcTimeRaw(time),
      sorter: (a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: "操作",
      key: "actions",
      width: 250,
      render: (text, record) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>

          {record.status === "pending" && (
            <Tooltip title="继续评测">
              <Button
                type="text"
                icon={<ReloadOutlined />}
                onClick={() => handleContinueEvaluation()}
              />
            </Tooltip>
          )}

          {record.status === "completed" && (
            <Tooltip title="导出结果">
              <Button
                type="text"
                icon={<DownloadOutlined />}
                onClick={() => handleExport(record.id)}
              />
            </Tooltip>
          )}

          <Tooltip title="查看JSON">
            <Button
              type="text"
              icon={<RobotOutlined />}
              onClick={() => handleShowJson(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <Layout className="evaluation-history-page">
      <Content style={{ padding: "24px", background: "#f0f2f5" }}>
        {/* 页面标题已移除，使用顶部导航栏 */}
        <div style={{ marginBottom: 24 }}>
          <Row justify="end" align="middle">
            <Col>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreateNew}
                size="large"
              >
                创建新评测
              </Button>
            </Col>
          </Row>
        </div>

        {/* 统计卡片 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总评测数"
                value={pagination.total}
                prefix={<HistoryOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="已完成"
                value={sessions.filter((s) => s.status === "completed").length}
                prefix={<CheckCircleOutlined style={{ color: "#52c41a" }} />}
                valueStyle={{ color: "#52c41a" }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="运行中"
                value={sessions.filter((s) => s.status === "running").length}
                prefix={<ClockCircleOutlined style={{ color: "#faad14" }} />}
                valueStyle={{ color: "#faad14" }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="失败数"
                value={sessions.filter((s) => s.status === "failed").length}
                prefix={
                  <ExclamationCircleOutlined style={{ color: "#ff4d4f" }} />
                }
                valueStyle={{ color: "#ff4d4f" }}
              />
            </Card>
          </Col>
        </Row>

        {/* 搜索和筛选 */}
        <Card style={{ marginBottom: 24 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Search
                placeholder="搜索评测名称或ID"
                allowClear
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                onSearch={loadSessions}
                enterButton={<SearchOutlined />}
              />
            </Col>
            <Col span={4}>
              <Select
                placeholder="状态筛选"
                allowClear
                style={{ width: "100%" }}
                value={statusFilter || undefined}
                onChange={(value) => setStatusFilter(value || "")}
              >
                <Option value="pending">等待中</Option>
                <Option value="running">运行中</Option>
                <Option value="completed">已完成</Option>
                <Option value="failed">失败</Option>
                <Option value="cancelled">已取消</Option>
              </Select>
            </Col>
            <Col span={8}>
              <RangePicker
                style={{ width: "100%" }}
                placeholder={["开始日期", "结束日期"]}
                value={dateRange}
                onChange={setDateRange}
              />
            </Col>
            <Col span={4}>
              <Button
                icon={<FilterOutlined />}
                onClick={loadSessions}
                style={{ width: "100%" }}
              >
                筛选
              </Button>
            </Col>
          </Row>
        </Card>

        {/* 批量操作工具栏 */}
        {selectedRowKeys.length > 0 && (
          <Card
            style={{
              marginBottom: 16,
              backgroundColor: "#f6ffed",
              border: "1px solid #b7eb8f",
            }}
          >
            <Row justify="space-between" align="middle">
              <Col>
                <Space>
                  <Text strong>已选择 {selectedRowKeys.length} 个评测会话</Text>
                  <Button type="link" onClick={() => setSelectedRowKeys([])}>
                    清空选择
                  </Button>
                </Space>
              </Col>
              <Col>
                <Space>
                  <Button
                    icon={<DownloadOutlined />}
                    onClick={handleBatchExport}
                    loading={batchLoading}
                  >
                    批量导出
                  </Button>
                  <Button
                    danger
                    icon={<StopOutlined />}
                    onClick={handleBatchDelete}
                    loading={batchLoading}
                  >
                    批量删除
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>
        )}

        {/* 评测会话表格 */}
        <Card>
          <Table
            columns={columns}
            dataSource={sessions}
            rowKey="id"
            loading={loading}
            rowSelection={{
              selectedRowKeys,
              onChange: (keys) => setSelectedRowKeys(keys as string[]),
              getCheckboxProps: (record) => ({
                disabled: record.status === "running", // 正在运行的会话不允许删除
              }),
            }}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) =>
                `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`,
              onChange: (page, pageSize) => {
                setPagination((prev) => ({
                  ...prev,
                  current: page,
                  pageSize: pageSize || prev.pageSize,
                }));
              },
            }}
            scroll={{ x: 1200 }}
          />
        </Card>

        {/* 详情模态框 */}
        <Modal
          title={`评测会话详情 - ${selectedSession?.name}`}
          open={detailModalVisible}
          onCancel={() => {
            setDetailModalVisible(false);
            setSelectedSession(null);
            setSessionResults([]);
          }}
          width={1400}
          footer={null}
          destroyOnHidden
        >
          {selectedSession && (
            <div>
              {/* 会话概览信息 */}
              <Card size="small" style={{ marginBottom: 16 }}>
                <Row gutter={16}>
                  <Col span={6}>
                    <Text type="secondary">状态: </Text>
                    <Tag
                      color={
                        selectedSession.status === "completed"
                          ? "green"
                          : "orange"
                      }
                    >
                      {selectedSession.status}
                    </Tag>
                  </Col>
                  <Col span={6}>
                    <Text type="secondary">智能体数量: </Text>
                    <Text strong>
                      {selectedSession.selected_agents?.length || 0}
                    </Text>
                  </Col>
                  <Col span={6}>
                    <Text type="secondary">问题数量: </Text>
                    <Text strong>{selectedSession.questions?.length || 0}</Text>
                  </Col>
                  <Col span={6}>
                    <Text type="secondary">创建时间 (UTC): </Text>
                    <Text>{formatUtcTimeRaw(selectedSession.created_at)}</Text>
                  </Col>
                </Row>
              </Card>

              {/* 多角色对话记录 */}
              <MultiAgentChatDisplay
                session={selectedSession}
                results={sessionResults}
                loading={resultsLoading}
                showControls={true}
              />
            </div>
          )}
        </Modal>

        {/* JSON数据展示模态框 */}
        <JsonDisplayModal
          open={jsonModalVisible}
          onClose={hideJson}
          title="评测结果JSON数据"
          jsonData={jsonData}
        />
      </Content>
    </Layout>
  );
};
