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
  Select,
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
  QuestionCircleOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { festivalMemoryApi } from "../services/api";
import type {
  FestivalMemoryConfigItem,
  FestivalMemoryConfigCreate,
  FestivalMemoryConfigResultResponse,
  FestivalMemoryConfigUpdate,
  FestivalMemoryExtractionRunResponse,
  FestivalMemoryResultItem,
} from "../types";
import {
  canShowFestivalMemoryResults,
  getFestivalMemoryRunStatusMeta,
  resolveFestivalMemoryRunStatus,
} from "../utils/festivalMemory";

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

export const FestivalMemoryPage: React.FC = () => {
  const [configs, setConfigs] = useState<FestivalMemoryConfigItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [runLoading, setRunLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [docModalOpen, setDocModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formName, setFormName] = useState("");
  const [formDate, setFormDate] = useState<dayjs.Dayjs | null>(null);
  const [formTimezone, setFormTimezone] = useState<string>("UTC");
  const [formPrompt, setFormPrompt] = useState("");
  const [formEnabled, setFormEnabled] = useState(true);
  const [formRunAtDate, setFormRunAtDate] = useState<dayjs.Dayjs | null>(null);
  const [formRunAtHour, setFormRunAtHour] = useState<number>(4);
  const [formMinRounds, setFormMinRounds] = useState<number | null>(null);
  const [resultModalOpen, setResultModalOpen] = useState(false);
  const [resultLoading, setResultLoading] = useState(false);
  const [selectedResultConfig, setSelectedResultConfig] =
    useState<FestivalMemoryConfigItem | null>(null);
  const [resultData, setResultData] =
    useState<FestivalMemoryConfigResultResponse | null>(null);

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

  React.useEffect(() => {
    const timer = window.setInterval(() => {
      loadConfigs();
    }, 15000);
    return () => window.clearInterval(timer);
  }, [loadConfigs]);

  const openCreate = () => {
    setEditingId(null);
    setFormName("");
    setFormDate(null);
    setFormTimezone("UTC");
    setFormPrompt("");
    setFormEnabled(true);
    setFormRunAtDate(null);
    setFormRunAtHour(4);
    setFormMinRounds(null);
    setModalOpen(true);
  };

  const openEdit = (row: FestivalMemoryConfigItem) => {
    setEditingId(row.id);
    setFormName(row.festival_name);
    setFormDate(row.festival_date ? dayjs(row.festival_date) : null);
    setFormTimezone(row.timezone ?? "UTC");
    setFormPrompt(row.prompt);
    setFormEnabled(row.enabled);
    setFormRunAtDate(row.run_at_date ? dayjs(row.run_at_date) : null);
    setFormRunAtHour(
      row.run_at_hour != null && row.run_at_hour >= 0 && row.run_at_hour <= 23
        ? row.run_at_hour
        : 4,
    );
    setFormMinRounds(
      row.min_rounds_in_window != null && row.min_rounds_in_window >= 1
        ? row.min_rounds_in_window
        : null,
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
      message.warning("执行时刻（该时区本地小时）须为 0–23");
      return;
    }
    try {
      if (editingId != null) {
        const update: FestivalMemoryConfigUpdate = {
          festival_name: formName.trim(),
          festival_date: dateStr,
          prompt: formPrompt.trim(),
          enabled: formEnabled,
          timezone: formTimezone,
          run_at_date: runAtDateStr,
          run_at_hour: hour,
          min_rounds_in_window: formMinRounds ?? undefined,
        };
        await festivalMemoryApi.updateConfig(editingId, update);
        message.success("更新成功");
      } else {
        const create: FestivalMemoryConfigCreate = {
          festival_name: formName.trim(),
          festival_date: dateStr,
          prompt: formPrompt.trim(),
          enabled: formEnabled,
          timezone: formTimezone,
          run_at_date: runAtDateStr,
          run_at_hour: hour,
          min_rounds_in_window: formMinRounds ?? undefined,
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

  const formatDateTime = (value: string | null | undefined): string => {
    if (!value) return "-";
    const dt = dayjs(value);
    return dt.isValid() ? dt.format("YYYY-MM-DD HH:mm") : value;
  };

  const handleShowResults = async (row: FestivalMemoryConfigItem) => {
    setSelectedResultConfig(row);
    setResultModalOpen(true);
    setResultLoading(true);
    setResultData(null);
    try {
      const data = await festivalMemoryApi.getConfigResults(row.id, { limit: 10 });
      setResultData(data);
    } catch {
      message.error("加载结果失败");
      setResultData(null);
    } finally {
      setResultLoading(false);
    }
  };

  const resultColumns: ColumnsType<FestivalMemoryResultItem> = [
    {
      title: "提取时间",
      dataIndex: "extracted_at",
      key: "extracted_at",
      width: 180,
      render: (v: string) => formatDateTime(v),
    },
    {
      title: "用户ID",
      dataIndex: "user_id",
      key: "user_id",
      width: 180,
      ellipsis: true,
    },
    {
      title: "角色ID",
      dataIndex: "agent_id",
      key: "agent_id",
      width: 180,
      ellipsis: true,
    },
    {
      title: "记忆内容",
      dataIndex: "memory",
      key: "memory",
      render: (v: string) => (v && v.length > 200 ? `${v.slice(0, 200)}...` : v),
    },
  ];

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
      title: "运行情况",
      key: "run_status",
      width: 180,
      render: (_, row) => {
        const status = resolveFestivalMemoryRunStatus(row);
        const meta = getFestivalMemoryRunStatusMeta(status);
        return (
          <Space direction="vertical" size={2}>
            <Tag color={meta.color}>{meta.label}</Tag>
            {status === "running" && row.run_started_at ? (
              <Text type="secondary">{`开始：${formatDateTime(row.run_started_at)}`}</Text>
            ) : null}
            {status !== "running" &&
            (row.run_finished_at || row.last_run_at) ? (
              <Text type="secondary">
                {`结束：${formatDateTime(row.run_finished_at || row.last_run_at)}`}
              </Text>
            ) : null}
            {row.run_total_pairs != null ? (
              <Text type="secondary">
                {`总 ${row.run_total_pairs} / 成 ${row.run_success_count ?? 0} / 败 ${row.run_failed_count ?? 0}`}
              </Text>
            ) : null}
          </Space>
        );
      },
    },
    {
      title: "最近执行",
      dataIndex: "last_run_at",
      key: "last_run_at",
      width: 180,
      render: (v: string | null) => formatDateTime(v),
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
      width: 300,
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
            disabled={!!row.last_run_at}
            title={
              row.last_run_at ? "该配置已执行过，不可再次立即执行" : undefined
            }
            onClick={() => handleRun(row)}
          >
            立即执行
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            disabled={!canShowFestivalMemoryResults(row)}
            title={
              canShowFestivalMemoryResults(row)
                ? undefined
                : "后台任务尚未结束，暂无可展示结果"
            }
            onClick={() => handleShowResults(row)}
          >
            显示结果
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
          表。系统将按配置的定时任务自动执行提取；也可在此对单条配置点击「立即执行」。任务结束后可点击「显示结果」查看最多
          10 条记忆数据。
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
            <Text strong>时区</Text>
            <br />
            <Select
              value={formTimezone}
              onChange={setFormTimezone}
              options={FESTIVAL_TIMEZONE_OPTIONS}
              style={{ width: "100%", marginTop: 4 }}
            />
            <Text
              type="secondary"
              style={{ fontSize: 12, marginTop: 4, display: "block" }}
            >
              节日日期与执行日期/时刻均按此时区下的本地值
            </Text>
          </div>
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
            <Text strong>节日日期（该时区下的自然日）</Text>
            <br />
            <DatePicker
              value={formDate}
              onChange={(d) => setFormDate(d)}
              style={{ width: "100%", marginTop: 4 }}
            />
          </div>
          <div>
            <Space style={{ marginBottom: 4 }}>
              <Text strong>执行日期（该时区下本地日期）</Text>
              <Button
                type="link"
                size="small"
                onClick={() => {
                  const now = new Date();
                  try {
                    const fmt = new Intl.DateTimeFormat("en-CA", {
                      timeZone: formTimezone,
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
                    setFormRunAtDate(dayjs(`${y}-${m}-${d}`));
                    setFormRunAtHour(h >= 0 && h <= 23 ? h : 0);
                  } catch {
                    const utcDateStr = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}-${String(now.getUTCDate()).padStart(2, "0")}`;
                    setFormRunAtDate(dayjs(utcDateStr));
                    setFormRunAtHour(now.getUTCHours());
                  }
                }}
              >
                设为当前所选时区的本地时间
              </Button>
            </Space>
            <DatePicker
              value={formRunAtDate}
              onChange={(d) => setFormRunAtDate(d)}
              style={{ width: "100%", marginTop: 4 }}
            />
            <Text
              type="secondary"
              style={{ fontSize: 12, marginTop: 4, display: "block" }}
            >
              不能早于节日日期；定时任务每 5 分钟扫描，到点后执行一次
            </Text>
          </div>
          <div>
            <Text strong>执行时刻（该时区下本地小时 0–23）</Text>
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
            <Text strong>窗口内最少用户消息数</Text>
            <br />
            <InputNumber
              min={1}
              value={formMinRounds ?? undefined}
              onChange={(v) => setFormMinRounds(v ?? null)}
              placeholder="留空表示默认 15"
              style={{ width: "100%", marginTop: 4 }}
            />
            <Text
              type="secondary"
              style={{ fontSize: 12, marginTop: 4, display: "block" }}
            >
              留空表示默认 15；仅对窗口内用户消息数达到该值的 (用户, 角色) 抽取
            </Text>
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
              <Text style={{ marginLeft: 8 }}>
                启用（定时任务会执行该配置）
              </Text>
            </label>
          </div>
        </Space>
      </Modal>

      <Modal
        title={
          selectedResultConfig
            ? `节日结果：${selectedResultConfig.festival_name}（最多 10 条）`
            : "节日结果（最多 10 条）"
        }
        open={resultModalOpen}
        onCancel={() => {
          setResultModalOpen(false);
          setSelectedResultConfig(null);
          setResultData(null);
        }}
        width={900}
        footer={
          <Button
            type="primary"
            onClick={() => {
              setResultModalOpen(false);
              setSelectedResultConfig(null);
              setResultData(null);
            }}
          >
            关闭
          </Button>
        }
      >
        <Space direction="vertical" style={{ width: "100%" }} size="small">
          {resultData ? (
            <Text type="secondary">
              {`状态：${getFestivalMemoryRunStatusMeta(resultData.run_status).label}；总 ${resultData.run_total_pairs ?? "-"} / 成 ${resultData.run_success_count ?? "-"} / 败 ${resultData.run_failed_count ?? "-"}`}
            </Text>
          ) : null}
          {resultData?.run_error_message ? (
            <Text type="danger">{`错误信息：${resultData.run_error_message}`}</Text>
          ) : null}
          <Table
            rowKey="memory_id"
            size="small"
            loading={resultLoading}
            columns={resultColumns}
            dataSource={resultData?.items ?? []}
            pagination={false}
            locale={{ emptyText: "暂无结果数据" }}
            scroll={{ x: 860 }}
          />
        </Space>
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
              该时刻且该配置尚未在此执行时刻跑过时执行一次，执行后更新「最近执行」时间，同一时刻只执行一次。也可对单条配置点击「立即执行」手动触发。执行日期不能早于节日日期。
            </Text>
          </div>
          <div>
            <Title level={5}>操作说明</Title>
            <Text>
              新建/编辑：填写时区、节日名称、节日日期（该时区自然日）、执行日期与执行时刻（该时区本地）、可选「窗口内最少用户消息数」（不填则默认
              15）、抽取提示词、是否启用。可点击「设为当前所选时区的本地时间」快速填入执行时间。删除可移除配置；已执行过的配置不可再次「立即执行」。
            </Text>
          </div>
        </Space>
      </Modal>
    </div>
  );
};
