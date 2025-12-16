/**
 * 举报与反馈分析页面
 * 展示用户举报(Report)和反馈(Feedback)列表，支持筛选
 * CREATED_BY_AGENT
 */

import React, { useState, useEffect, useCallback } from "react";
import {
  Card,
  Table,
  Tag,
  Select,
  Button,
  Space,
  Image,
  Modal,
  Descriptions,
  message,
  Empty,
} from "antd";
import { ReloadOutlined, EyeOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { reportApi } from "../services/api";
import type {
  ReportItem,
  ReportTargetType,
  ReportStatus,
  ReportType,
} from "../types";

const { Option } = Select;

// 原因代码中文映射
const REASON_CODE_LABELS: Record<string, string> = {
  SENSITIVE_CONTENT: "敏感内容",
  MISINFORMATION: "虚假信息",
  FRAUD_SCAMS: "欺诈诈骗",
  PRIVACY_VIOLATION: "隐私侵犯",
  HARMFUL_MINORS: "有害未成年人",
  IP_VIOLATION: "侵犯知识产权",
  OTHER: "其他",
  CHAT_NOT_NATURAL: "聊天不自然",
  CHARACTER_MISMATCH: "角色不匹配",
  APP_SLOW: "应用运行慢",
  FEATURE_HARD_TO_FIND: "功能难找",
  UI_INCONVENIENT: "UI不便",
  NEW_FEATURE: "新功能建议",
};

// 状态颜色映射
const STATUS_COLORS: Record<ReportStatus, string> = {
  PENDING: "orange",
  PROCESSING: "blue",
  RESOLVED: "green",
  REJECTED: "red",
};

// 状态中文映射
const STATUS_LABELS: Record<ReportStatus, string> = {
  PENDING: "待处理",
  PROCESSING: "处理中",
  RESOLVED: "已处理",
  REJECTED: "已驳回",
};

// 类型颜色映射
const TYPE_COLORS: Record<ReportType, string> = {
  REPORT: "volcano",
  FEEDBACK: "cyan",
};

// 类型中文映射
const TYPE_LABELS: Record<ReportType, string> = {
  REPORT: "举报",
  FEEDBACK: "反馈",
};

export const ReportFeedbackPage: React.FC = () => {
  // 筛选状态
  const [reportType, setReportType] = useState<ReportType | undefined>(
    undefined,
  );
  const [status, setStatus] = useState<ReportStatus | undefined>(undefined);
  const [targetType, setTargetType] = useState<ReportTargetType | undefined>(
    undefined,
  );
  const [orderBy, setOrderBy] = useState<"created_at_desc" | "created_at_asc">(
    "created_at_desc",
  );

  // 数据状态
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ReportItem[]>([]);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 });

  // 详情弹窗状态
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedItem, setSelectedItem] = useState<ReportItem | null>(null);

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await reportApi.list({
        report_type: reportType,
        status: status,
        target_type: targetType,
        order_by: orderBy,
        skip: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
      });
      setData(result.items);
      setTotal(result.total);
    } catch (error) {
      console.error("加载数据失败:", error);
      message.error("加载数据失败");
    } finally {
      setLoading(false);
    }
  }, [reportType, status, targetType, orderBy, pagination]);

  // 初始化加载
  useEffect(() => {
    loadData();
  }, [loadData]);

  // 查看详情
  const handleViewDetail = (record: ReportItem) => {
    setSelectedItem(record);
    setDetailVisible(true);
  };

  // 表格列定义
  const columns: ColumnsType<ReportItem> = [
    {
      title: "ID",
      dataIndex: "id",
      key: "id",
      width: 120,
      ellipsis: true,
      render: (id: string) => <span title={id}>{id.substring(0, 8)}...</span>,
    },
    {
      title: "类型",
      dataIndex: "report_type",
      key: "report_type",
      width: 80,
      render: (type: ReportType | null) => {
        const displayType = type || "REPORT";
        return (
          <Tag color={TYPE_COLORS[displayType]}>{TYPE_LABELS[displayType]}</Tag>
        );
      },
    },
    {
      title: "目标类型",
      dataIndex: "target_type",
      key: "target_type",
      width: 90,
      render: (type: ReportTargetType) => (
        <Tag color={type === "USER" ? "purple" : "geekblue"}>
          {type === "USER" ? "用户" : "角色"}
        </Tag>
      ),
    },
    {
      title: "目标ID",
      dataIndex: "target_id",
      key: "target_id",
      width: 140,
      ellipsis: true,
      render: (id: string) => <span title={id}>{id.substring(0, 12)}...</span>,
    },
    {
      title: "原因",
      dataIndex: "reason_codes",
      key: "reason_codes",
      width: 200,
      render: (codes: string[]) => (
        <Space wrap size={[0, 4]}>
          {codes.map((code) => (
            <Tag key={code} color="default">
              {REASON_CODE_LABELS[code] || code}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 90,
      render: (status: ReportStatus) => (
        <Tag color={STATUS_COLORS[status]}>{STATUS_LABELS[status]}</Tag>
      ),
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      width: 200,
      ellipsis: true,
      render: (desc: string | null) => {
        if (!desc) return <span style={{ color: "#999" }}>无</span>;
        const maxLen = 50;
        const displayText =
          desc.length > maxLen ? `${desc.substring(0, maxLen)}...` : desc;
        return <span title={desc}>{displayText}</span>;
      },
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 170,
      render: (time: string) => dayjs(time).format("YYYY-MM-DD HH:mm:ss"),
    },
    {
      title: "操作",
      key: "action",
      width: 80,
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
        >
          详情
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: "24px" }}>
      {/* 筛选区域 */}
      <Card style={{ marginBottom: "24px" }}>
        <Space wrap size="middle">
          <span style={{ fontWeight: 500 }}>筛选：</span>

          <Select
            placeholder="类型"
            value={reportType}
            onChange={setReportType}
            allowClear
            style={{ width: 120 }}
          >
            <Option value="REPORT">举报</Option>
            <Option value="FEEDBACK">反馈</Option>
          </Select>

          <Select
            placeholder="状态"
            value={status}
            onChange={setStatus}
            allowClear
            style={{ width: 120 }}
          >
            <Option value="PENDING">待处理</Option>
            <Option value="PROCESSING">处理中</Option>
            <Option value="RESOLVED">已处理</Option>
            <Option value="REJECTED">已驳回</Option>
          </Select>

          <Select
            placeholder="目标类型"
            value={targetType}
            onChange={setTargetType}
            allowClear
            style={{ width: 120 }}
          >
            <Option value="USER">用户</Option>
            <Option value="AGENT">角色</Option>
          </Select>

          <Select value={orderBy} onChange={setOrderBy} style={{ width: 150 }}>
            <Option value="created_at_desc">创建时间降序</Option>
            <Option value="created_at_asc">创建时间升序</Option>
          </Select>

          <Button
            icon={<ReloadOutlined />}
            onClick={loadData}
            loading={loading}
          >
            刷新
          </Button>
        </Space>
      </Card>

      {/* 数据表格 */}
      <Card title={`举报与反馈列表 (共 ${total} 条)`}>
        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            pageSizeOptions: ["10", "20", "50", "100"],
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => {
              setPagination({ current: page, pageSize: pageSize || 20 });
            },
          }}
          locale={{
            emptyText: <Empty description="暂无数据" />,
          }}
        />
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title="举报/反馈详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={700}
      >
        {selectedItem && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="ID" span={2}>
              {selectedItem.id}
            </Descriptions.Item>
            <Descriptions.Item label="类型">
              <Tag color={TYPE_COLORS[selectedItem.report_type || "REPORT"]}>
                {TYPE_LABELS[selectedItem.report_type || "REPORT"]}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={STATUS_COLORS[selectedItem.status]}>
                {STATUS_LABELS[selectedItem.status]}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="目标类型">
              <Tag
                color={
                  selectedItem.target_type === "USER" ? "purple" : "geekblue"
                }
              >
                {selectedItem.target_type === "USER" ? "用户" : "角色"}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="目标ID">
              {selectedItem.target_id}
            </Descriptions.Item>
            <Descriptions.Item label="举报人ID" span={2}>
              {selectedItem.reporter_id}
            </Descriptions.Item>
            <Descriptions.Item label="原因" span={2}>
              <Space wrap>
                {selectedItem.reason_codes.map((code) => (
                  <Tag key={code} color="blue">
                    {REASON_CODE_LABELS[code] || code}
                  </Tag>
                ))}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="描述" span={2}>
              {selectedItem.description || "无"}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间" span={2}>
              {dayjs(selectedItem.created_at).format("YYYY-MM-DD HH:mm:ss")}
            </Descriptions.Item>
            {selectedItem.image_urls && selectedItem.image_urls.length > 0 && (
              <Descriptions.Item label="附图" span={2}>
                <Image.PreviewGroup>
                  <Space wrap>
                    {selectedItem.image_urls.map((url, index) => (
                      <Image
                        key={index}
                        src={url}
                        width={100}
                        height={100}
                        style={{ objectFit: "cover" }}
                      />
                    ))}
                  </Space>
                </Image.PreviewGroup>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};
