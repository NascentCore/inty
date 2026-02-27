/**
 * 节日记忆提取管理页
 * 管理员配置节日（名称、日期、提示词），由定时任务抽取 (user, agent) 节日回忆并写入 memory 表
 * 弹窗由单一 Form 驱动，与 AgentManagePage 一致。
 * CREATED_BY_AGENT
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  Checkbox,
  DatePicker,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  QuestionCircleOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { festivalMemoryApi } from "../services/api";
import modelCacheService from "../services/modelCache";
import LLMConfigForm from "../components/common/LLMConfigForm";
import type {
  FestivalMemoryConfigItem,
  FestivalMemoryConfigCreate,
  FestivalMemoryConfigUpdate,
  OpenRouterModel,
} from "../types";

const { Text, Title } = Typography;

const FESTIVAL_TIMEZONE_OPTIONS = [
  { value: "UTC", label: "UTC" },
  { value: "Asia/Shanghai", label: "Asia/Shanghai（中国）" },
  { value: "Asia/Hong_Kong", label: "Asia/Hong_Kong" },
  { value: "America/New_York", label: "America/New_York" },
  { value: "America/Los_Angeles", label: "America/Los_Angeles" },
  { value: "Europe/London", label: "Europe/London" },
  { value: "Europe/Paris", label: "Europe/Paris" },
  { value: "Japan", label: "Japan" },
];

const DEFAULT_FORM_VALUES = {
  timezone: "UTC",
  festival_name: "",
  festival_date: null as dayjs.Dayjs | null,
  prompt: "",
  enabled: true,
  run_at_date: null as dayjs.Dayjs | null,
  run_at_hour: 4,
  min_rounds_in_window: undefined as number | undefined,
  modelType: "default",
} as const;

export const FestivalMemoryPage: React.FC = () => {
  const [configs, setConfigs] = useState<FestivalMemoryConfigItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [docModalOpen, setDocModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [openRouterModels, setOpenRouterModels] = useState<OpenRouterModel[]>(
    [],
  );
  const [modelsLoading, setModelsLoading] = useState(false);

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

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  const loadModels = useCallback(async () => {
    setModelsLoading(true);
    try {
      const models = await modelCacheService.getOpenRouterModels();
      setOpenRouterModels(models);
    } catch {
      setOpenRouterModels([]);
    } finally {
      setModelsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (modalOpen) {
      loadModels();
    }
  }, [modalOpen, loadModels]);

  const openCreate = () => {
    setEditingId(null);
    setTimeout(() => {
      form.setFieldsValue({
        ...DEFAULT_FORM_VALUES,
      });
    }, 0);
    setModalOpen(true);
  };

  const openEdit = (row: FestivalMemoryConfigItem) => {
    setEditingId(row.id);
    setTimeout(() => {
      form.setFieldsValue({
        timezone: row.timezone ?? "UTC",
        festival_name: row.festival_name,
        festival_date: row.festival_date ? dayjs(row.festival_date) : null,
        prompt: row.prompt,
        enabled: row.enabled,
        run_at_date: row.run_at_date ? dayjs(row.run_at_date) : null,
        run_at_hour:
          row.run_at_hour != null &&
          row.run_at_hour >= 0 &&
          row.run_at_hour <= 23
            ? row.run_at_hour
            : 4,
        min_rounds_in_window:
          row.min_rounds_in_window != null && row.min_rounds_in_window >= 1
            ? row.min_rounds_in_window
            : undefined,
        modelType: row.llm_config ? "custom" : "default",
        ...(row.llm_config
          ? {
              model: row.llm_config.model || "",
              temperature: row.llm_config.temperature ?? 0.7,
              max_tokens: row.llm_config.max_tokens ?? 2048,
              top_p: row.llm_config.top_p ?? 1,
              frequency_penalty: row.llm_config.frequency_penalty ?? 0,
              presence_penalty: row.llm_config.presence_penalty ?? 0,
            }
          : {}),
      });
    }, 100);
    setModalOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const festivalDate = values.festival_date as dayjs.Dayjs | null;
      const runAtDate = values.run_at_date as dayjs.Dayjs | null;
      if (!festivalDate) {
        message.warning("请选择节日日期");
        return;
      }
      if (!runAtDate) {
        message.warning("请选择执行日期");
        return;
      }
      const dateStr = festivalDate.format("YYYY-MM-DD");
      const runAtDateStr = runAtDate.format("YYYY-MM-DD");
      if (runAtDate.isBefore(festivalDate, "day")) {
        message.warning("执行日期不能早于节日日期");
        return;
      }
      const hour = Math.floor(Number(values.run_at_hour ?? 4));
      if (hour < 0 || hour > 23) {
        message.warning("执行时刻（该时区本地小时）须为 0–23");
        return;
      }
      const customModel = (values.model ?? "").toString().trim();
      const llm_config =
        values.modelType === "custom" && customModel
          ? {
              model: customModel,
              temperature: Number(values.temperature ?? 0.7),
              max_tokens: Number(values.max_tokens ?? 2048),
              top_p: Number(values.top_p ?? 1),
              frequency_penalty: Number(values.frequency_penalty ?? 0),
              presence_penalty: Number(values.presence_penalty ?? 0),
            }
          : null;

      if (editingId != null) {
        const update: FestivalMemoryConfigUpdate = {
          festival_name: String(values.festival_name ?? "").trim(),
          festival_date: dateStr,
          prompt: String(values.prompt ?? "").trim(),
          enabled: Boolean(values.enabled),
          timezone: values.timezone ?? "UTC",
          run_at_date: runAtDateStr,
          run_at_hour: hour,
          min_rounds_in_window:
            values.min_rounds_in_window != null &&
            values.min_rounds_in_window >= 1
              ? Number(values.min_rounds_in_window)
              : undefined,
          llm_config,
        };
        await festivalMemoryApi.updateConfig(editingId, update);
        message.success("更新成功");
      } else {
        const create: FestivalMemoryConfigCreate = {
          festival_name: String(values.festival_name ?? "").trim(),
          festival_date: dateStr,
          prompt: String(values.prompt ?? "").trim(),
          enabled: Boolean(values.enabled),
          timezone: values.timezone ?? "UTC",
          run_at_date: runAtDateStr,
          run_at_hour: hour,
          min_rounds_in_window:
            values.min_rounds_in_window != null &&
            values.min_rounds_in_window >= 1
              ? Number(values.min_rounds_in_window)
              : undefined,
          llm_config,
        };
        await festivalMemoryApi.createConfig(create);
        message.success("创建成功");
      }
      setModalOpen(false);
      form.resetFields();
      loadConfigs();
    } catch (err) {
      if (err && typeof err === "object" && "errorFields" in err) {
        return;
      }
      message.error(editingId != null ? "更新失败" : "创建失败");
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
      title: "时区",
      dataIndex: "timezone",
      key: "timezone",
      width: 120,
      render: (v: string) => v || "UTC",
    },
    {
      title: "窗口最少消息数",
      dataIndex: "min_rounds_in_window",
      key: "min_rounds_in_window",
      width: 120,
      render: (v: number | null | undefined) =>
        v != null && v >= 1 ? String(v) : "默认 15",
    },
    {
      title: "执行日期",
      dataIndex: "run_at_date",
      key: "run_at_date",
      width: 120,
      render: (v: string | null) => v || "-",
    },
    {
      title: "执行时刻(本地)",
      dataIndex: "run_at_hour",
      key: "run_at_hour",
      width: 110,
      render: (v: number | null) => (v != null ? `${v}:00` : "-"),
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
      render: (v: string) =>
        v ? (v.length > 60 ? `${v.slice(0, 60)}...` : v) : "-",
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
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: "24px" }}>
      <Card
        title="节日记忆提取"
        extra={
          <Space>
            <Button
              type="link"
              icon={<QuestionCircleOutlined />}
              onClick={() => setDocModalOpen(true)}
            >
              使用文档
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新建配置
            </Button>
          </Space>
        }
      >
        <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
          按配置的时区：节日为「该时区下的自然日」，28 小时窗口为该自然日 0
          点至次日 4
          点；执行时间为该时区下的本地日期与时刻。仅对窗口内用户消息达到配置的「窗口内最少用户消息数」（可选，默认
          15 条）及以上的 (用户, 角色) 组合抽取节日回忆并写入 memory
          表。系统将按配置的定时任务自动执行提取。
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
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            ...DEFAULT_FORM_VALUES,
          }}
        >
          <Form.Item
            name="timezone"
            label="时区"
            rules={[{ required: true, message: "请选择时区" }]}
          >
            <Select
              options={FESTIVAL_TIMEZONE_OPTIONS}
              placeholder="选择时区"
            />
          </Form.Item>
          <Text
            type="secondary"
            style={{
              fontSize: 12,
              display: "block",
              marginTop: -8,
              marginBottom: 16,
            }}
          >
            节日日期与执行日期/时刻均按此时区下的本地值
          </Text>

          <Form.Item
            name="festival_name"
            label="节日名称"
            rules={[{ required: true, message: "请输入节日名称" }]}
          >
            <Input placeholder="如：春节" />
          </Form.Item>

          <Form.Item
            name="festival_date"
            label="节日日期（该时区下的自然日）"
            rules={[{ required: true, message: "请选择节日日期" }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item
            name="run_at_date"
            label={
              <Space>
                <span>执行日期（该时区下本地日期）</span>
                <Button
                  type="link"
                  size="small"
                  onClick={() => {
                    const timezone = form.getFieldValue("timezone") || "UTC";
                    const now = new Date();
                    try {
                      const fmt = new Intl.DateTimeFormat("en-CA", {
                        timeZone: timezone,
                        year: "numeric",
                        month: "2-digit",
                        day: "2-digit",
                        hour: "2-digit",
                        hour12: false,
                      });
                      const parts = fmt.formatToParts(now);
                      const part = (k: string) =>
                        parts.find((p) => p.type === k)?.value ?? "0";
                      const y = part("year");
                      const m = part("month").padStart(2, "0");
                      const d = part("day").padStart(2, "0");
                      const h = parseInt(part("hour"), 10);
                      form.setFieldsValue({
                        run_at_date: dayjs(`${y}-${m}-${d}`),
                        run_at_hour: h >= 0 && h <= 23 ? h : 0,
                      });
                    } catch {
                      const utcDateStr = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}-${String(now.getUTCDate()).padStart(2, "0")}`;
                      form.setFieldsValue({
                        run_at_date: dayjs(utcDateStr),
                        run_at_hour: now.getUTCHours(),
                      });
                    }
                  }}
                >
                  立刻执行
                </Button>
              </Space>
            }
            rules={[{ required: true, message: "请选择执行日期" }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Text
            type="secondary"
            style={{
              fontSize: 12,
              display: "block",
              marginTop: -8,
              marginBottom: 16,
            }}
          >
            不能早于节日日期；定时任务每 5 分钟扫描，到点后执行一次
          </Text>

          <Form.Item
            name="run_at_hour"
            label="执行时刻（该时区下本地小时 0–23）"
            rules={[
              { required: true, message: "请输入执行时刻" },
              { type: "number", min: 0, max: 23, message: "须为 0–23" },
            ]}
          >
            <InputNumber min={0} max={23} style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item name="min_rounds_in_window" label="窗口内最少用户消息数">
            <InputNumber
              min={1}
              placeholder="留空表示默认 15"
              style={{ width: "100%" }}
            />
          </Form.Item>
          <Text
            type="secondary"
            style={{
              fontSize: 12,
              display: "block",
              marginTop: -8,
              marginBottom: 16,
            }}
          >
            留空表示默认 15；仅对窗口内用户消息数达到该值的 (用户, 角色) 抽取
          </Text>

          <Form.Item
            name="prompt"
            label="抽取提示词"
            rules={[{ required: true, message: "请输入提示词" }]}
          >
            <Input.TextArea
              placeholder="用于 LLM 抽取该节日相关回忆的提示词"
              rows={6}
            />
          </Form.Item>

          <LLMConfigForm
            models={openRouterModels}
            loading={modelsLoading}
            onRefresh={loadModels}
          />

          <Form.Item name="enabled" valuePropName="checked" initialValue={true}>
            <Checkbox>启用（定时任务会执行该配置）</Checkbox>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="节日记忆提取 - 使用文档"
        open={docModalOpen}
        onCancel={() => setDocModalOpen(false)}
        width={640}
        footer={
          <Button type="primary" onClick={() => setDocModalOpen(false)}>
            关闭
          </Button>
        }
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <Title level={5}>功能概述</Title>
            <Text>
              本页用于配置「节日记忆」抽取：在指定节日时间窗口内，对用户与角色的对话达到一定条数的
              (用户, 角色) 组合，通过 LLM 抽取该节日相关回忆摘要并写入 memory
              表。抽取结果会在角色详情接口的 features.festival_memories
              中返回，供 App / Evaluation 展示（如「心跳日记」）。
            </Text>
          </div>
          <div>
            <Title level={5}>时区与日期</Title>
            <Text>
              每条配置需选择「时区」。节日日期、执行日期与执行时刻均为该时区下的本地值：节日日期表示「该时区下的自然日」；执行日期与执行时刻（0–23
              点）表示定时任务到点的本地日期与小时，系统会将其换算为 UTC
              后与当前时间比较。
            </Text>
          </div>
          <div>
            <Title level={5}>28 小时窗口</Title>
            <Text>
              抽取时间窗口为：该时区下「节日自然日 00:00 至次日 04:00」共 28
              小时（换算为 UTC
              后用于统计）。仅对在此窗口内用户消息数（排除开场白）≥
              配置的「窗口内最少用户消息数」（默认 15）的 (用户, 角色)
              组合进行抽取。
            </Text>
          </div>
          <div>
            <Title level={5}>执行方式</Title>
            <Text>
              定时任务每 5
              分钟扫描一次：若配置已启用且执行日期、执行时刻已填，系统会将
              (执行日期, 执行时刻) 按配置时区转为 UTC，当当前时间 ≥
              该时刻且该配置尚未在此执行时刻跑过时执行一次，执行后更新「最近执行」时间，同一时刻只执行一次。执行日期不能早于节日日期。
            </Text>
          </div>
          <div>
            <Title level={5}>操作说明</Title>
            <Text>
              新建/编辑：填写时区、节日名称、节日日期（该时区自然日）、执行日期与执行时刻（该时区本地）、可选「窗口内最少用户消息数」（不填则默认
              15）、抽取提示词、是否启用。可点击「立刻执行」快速填入执行时间。
            </Text>
          </div>
        </Space>
      </Modal>
    </div>
  );
};
