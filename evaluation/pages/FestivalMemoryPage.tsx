/**
 * 节日记忆提取管理页
 * 管理员配置节日（名称、日期、提示词），立即执行或由定时任务抽取 (user, agent) 节日回忆并写入 memory 表
 * CREATED_BY_AGENT
 */

import React, { useCallback, useState } from "react";
import {
  Button,
  Card,
  DatePicker,
  Input,
  InputNumber,
  message,
  Modal,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { festivalMemoryApi } from "../services/api";
import type {
  FestivalMemoryConfigItem,
  FestivalMemoryConfigCreate,
  FestivalMemoryConfigUpdate,
  FestivalMemoryExtractionRunResponse,
} from "../types";

const { Text } = Typography;

export const FestivalMemoryPage: React.FC = () => {
  const [configs, setConfigs] = useState<FestivalMemoryConfigItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [runLoading, setRunLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formName, setFormName] = useState("");
  const [formDate, setFormDate] = useState<dayjs.Dayjs | null>(null);
  const [formPrompt, setFormPrompt] = useState("");
  const [formEnabled, setFormEnabled] = useState(true);
  const [formRunAtDate, setFormRunAtDate] = useState<dayjs.Dayjs | null>(null);
  const [formRunAtHour, setFormRunAtHour] = useState<number>(4);

  const loadConfigs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await festivalMemoryApi.listConfigs({ skip: 0, limit: 100 });
      setConfigs(Array.isArray(data) ? data : []);
    } catch (e: unknown) {
      message.error("加载配置列表失败");
      setConfigs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  const openCreate = () => {
    setEditingId(null);
    setFormName("");
    setFormDate(null);
    setFormPrompt("");
    setFormEnabled(true);
    setFormRunAtDate(null);
    setFormRunAtHour(4);
    setModalOpen(true);
  };

  const openEdit = (row: FestivalMemoryConfigItem) => {
    setEditingId(row.id);
    setFormName(row.festival_name);
    setFormDate(row.festival_date ? dayjs(row.festival_date) : null);
    setFormPrompt(row.prompt);
    setFormEnabled(row.enabled);
    setFormRunAtDate(row.run_at_date ? dayjs(row.run_at_date) : null);
    setFormRunAtHour(
      row.run_at_hour != null && row.run_at_hour >= 0 && row.run_at_hour <= 23
        ? row.run_at_hour
        : 4,
    );
    setModalOpen(true);
  };

  const handleSave = async () => {
    if (!formName.trim()) {
      message.warning("请输入节日名称");
      return;
    }
    if (!formDate) {
      message.warning("请选择节日日期");
      return;
    }
    if (!formPrompt.trim()) {
      message.warning("请输入提示词");
      return;
    }
    if (!formRunAtDate) {
      message.warning("请选择执行日期");
      return;
    }
    const dateStr = formDate.format("YYYY-MM-DD");
    const runAtDateStr = formRunAtDate.format("YYYY-MM-DD");
    if (formRunAtDate.isBefore(formDate, "day")) {
      message.warning("执行日期不能早于节日日期");
      return;
    }
    const hour = Math.floor(formRunAtHour);
    if (hour < 0 || hour > 23) {
      message.warning("执行时刻（UTC 小时）须为 0–23");
      return;
    }
    try {
      if (editingId != null) {
        const update: FestivalMemoryConfigUpdate = {
          festival_name: formName.trim(),
          festival_date: dateStr,
          prompt: formPrompt.trim(),
          enabled: formEnabled,
          run_at_date: runAtDateStr,
          run_at_hour: hour,
        };
        await festivalMemoryApi.updateConfig(editingId, update);
        message.success("更新成功");
      } else {
        const create: FestivalMemoryConfigCreate = {
          festival_name: formName.trim(),
          festival_date: dateStr,
          prompt: formPrompt.trim(),
          enabled: formEnabled,
          run_at_date: runAtDateStr,
          run_at_hour: hour,
        };
        await festivalMemoryApi.createConfig(create);
        message.success("创建成功");
      }
      setModalOpen(false);
      loadConfigs();
    } catch {
      message.error(editingId != null ? "更新失败" : "创建失败");
    }
  };

  const handleDelete = (row: FestivalMemoryConfigItem) => {
    Modal.confirm({
      title: "确认删除",
      content: `确定删除节日「${row.festival_name}」的配置吗？`,
      onOk: async () => {
        try {
          await festivalMemoryApi.deleteConfig(row.id);
          message.success("已删除");
          loadConfigs();
        } catch {
          message.error("删除失败");
        }
      },
    });
  };

  const handleRun = async (row: FestivalMemoryConfigItem) => {
    setRunLoading(true);
    try {
      const result = (await festivalMemoryApi.runExtraction({
        config_id: row.id,
      })) as FestivalMemoryExtractionRunResponse;
      message.success(
        `执行完成：共 ${result.total_pairs} 对，成功 ${result.success_count}，失败 ${result.failed_count}`,
      );
      loadConfigs();
    } catch {
      message.error("执行失败");
    } finally {
      setRunLoading(false);
    }
  };

  const columns: ColumnsType<FestivalMemoryConfigItem> = [
    {
      title: "节日名称",
      dataIndex: "festival_name",
      key: "festival_name",
      width: 140,
    },
    {
      title: "节日日期",
      dataIndex: "festival_date",
      key: "festival_date",
      width: 120,
      render: (v: string) => v || "-",
    },
    {
      title: "执行日期",
      dataIndex: "run_at_date",
      key: "run_at_date",
      width: 120,
      render: (v: string | null) => v || "-",
    },
    {
      title: "执行时刻(UTC)",
      dataIndex: "run_at_hour",
      key: "run_at_hour",
      width: 110,
      render: (v: number | null) =>
        v != null ? `${v}:00` : "-",
    },
    {
      title: "最近执行",
      dataIndex: "last_run_at",
      key: "last_run_at",
      width: 180,
      render: (v: string | null) =>
        v ? dayjs(v).format("YYYY-MM-DD HH:mm") : "-",
    },
    {
      title: "提示词摘要",
      dataIndex: "prompt",
      key: "prompt",
      ellipsis: true,
      render: (v: string) => (v ? (v.length > 60 ? `${v.slice(0, 60)}...` : v) : "-"),
    },
    {
      title: "启用",
      dataIndex: "enabled",
      key: "enabled",
      width: 80,
      render: (v: boolean) =>
        v ? <Tag color="green">是</Tag> : <Tag color="default">否</Tag>,
    },
    {
      title: "操作",
      key: "actions",
      width: 200,
      render: (_, row) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEdit(row)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            icon={<PlayCircleOutlined />}
            loading={runLoading}
            onClick={() => handleRun(row)}
          >
            立即执行
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(row)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: "24px" }}>
      <Card
        title="节日记忆提取"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建配置
          </Button>
        }
      >
        <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
          仅对「用户 + 角色」聊天轮数 ≥ 30 的组合抽取节日回忆并写入 memory
          表。系统将按配置的定时任务自动执行提取；也可在此对单条配置点击「立即执行」。
        </Text>
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={configs}
          pagination={false}
        />
      </Card>

      <Modal
        title={editingId != null ? "编辑节日记忆配置" : "新建节日记忆配置"}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        width={560}
        okText="保存"
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <Text strong>节日名称</Text>
            <br />
            <Input
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="如：春节"
              style={{ width: "100%", marginTop: 4 }}
            />
          </div>
          <div>
            <Text strong>节日日期</Text>
            <br />
            <DatePicker
              value={formDate}
              onChange={(d) => setFormDate(d)}
              style={{ width: "100%", marginTop: 4 }}
            />
          </div>
          <div>
            <Space style={{ marginBottom: 4 }}>
              <Text strong>执行日期</Text>
              <Button
                type="link"
                size="small"
                onClick={() => {
                  const now = new Date();
                  const utcDateStr = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}-${String(now.getUTCDate()).padStart(2, "0")}`;
                  setFormRunAtDate(dayjs(utcDateStr));
                  setFormRunAtHour(now.getUTCHours());
                }}
              >
                立刻执行（设为当前 UTC 时间）
              </Button>
            </Space>
            <DatePicker
              value={formRunAtDate}
              onChange={(d) => setFormRunAtDate(d)}
              style={{ width: "100%", marginTop: 4 }}
            />
            <Text type="secondary" style={{ fontSize: 12, marginTop: 4, display: "block" }}>
              不能早于节日日期；定时任务每 5 分钟扫描，到点后执行一次
            </Text>
          </div>
          <div>
            <Text strong>执行时刻（UTC 小时）</Text>
            <br />
            <InputNumber
              min={0}
              max={23}
              value={formRunAtHour}
              onChange={(v) => setFormRunAtHour(v ?? 4)}
              style={{ width: "100%", marginTop: 4 }}
            />
          </div>
          <div>
            <Text strong>抽取提示词</Text>
            <br />
            <Input.TextArea
              value={formPrompt}
              onChange={(e) => setFormPrompt(e.target.value)}
              placeholder="用于 LLM 抽取该节日相关回忆的提示词"
              rows={6}
              style={{ width: "100%", marginTop: 4 }}
            />
          </div>
          <div>
            <label>
              <input
                type="checkbox"
                checked={formEnabled}
                onChange={(e) => setFormEnabled(e.target.checked)}
              />
              <Text style={{ marginLeft: 8 }}>启用（定时任务会执行该配置）</Text>
            </label>
          </div>
        </Space>
      </Modal>
    </div>
  );
};
