/**
 * 大模型月度账单计算器页面
 * 支持手动录入模型定价、按“先用量后选模型”流程计算多模型账单明细。
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Steps,
  Table,
  Tag,
  Typography,
} from "antd";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import type {
  ModelMonthlyBill,
  ModelPricingData,
  MonthlyUsageData,
} from "../utils/monthlyBillingCalculator";
import {
  calculateMonthlyBills,
  calculateSelectedModelsTotal,
  findDuplicateModelIds,
  isUsageDataValid,
  toPricingMap,
} from "../utils/monthlyBillingCalculator";

const { Title, Text } = Typography;

interface PricingRow extends ModelPricingData {
  rowId: number;
}

const createPricingRow = (rowId: number): PricingRow => ({
  rowId,
  modelId: "",
  inputPerMillionUsd: 0,
  outputPerMillionUsd: 0,
  cacheReadPerMillionUsd: 0,
  cacheWritePerMillionUsd: 0,
});

const normalizeNonNegativeNumber = (value: number | null): number => {
  if (value == null || Number.isNaN(value)) return 0;
  return value < 0 ? 0 : value;
};

const normalizeNonNegativeInteger = (value: number | null): number =>
  Math.floor(normalizeNonNegativeNumber(value));

const formatUsd = (value: number): string => `$${value.toFixed(6)}`;

export const LlmMonthlyBillingPage: React.FC = () => {
  const [usageDraft, setUsageDraft] = useState<MonthlyUsageData>({
    inputTokens: 0,
    outputTokens: 0,
    cacheReadTokens: 0,
    cacheWriteTokens: 0,
  });
  const [confirmedUsage, setConfirmedUsage] = useState<MonthlyUsageData | null>(
    null,
  );
  const [pricingRows, setPricingRows] = useState<PricingRow[]>([
    createPricingRow(1),
  ]);
  const [nextPricingRowId, setNextPricingRowId] = useState(2);
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);
  const [hasCalculated, setHasCalculated] = useState(false);

  const duplicateModelIds = useMemo(
    () => findDuplicateModelIds(pricingRows),
    [pricingRows],
  );
  const hasDuplicateModelIds = duplicateModelIds.length > 0;

  const pricingMap = useMemo(() => {
    if (hasDuplicateModelIds) {
      return new Map<string, ModelPricingData>();
    }
    return toPricingMap(pricingRows);
  }, [hasDuplicateModelIds, pricingRows]);

  const modelOptions = useMemo(
    () =>
      Array.from(pricingMap.keys()).map((modelId) => ({
        label: modelId,
        value: modelId,
      })),
    [pricingMap],
  );

  useEffect(() => {
    setSelectedModelIds((prev) =>
      prev.filter((modelId) => pricingMap.has(modelId)),
    );
  }, [pricingMap]);

  const canConfirmUsage = isUsageDataValid(usageDraft);
  const canSelectModels =
    confirmedUsage !== null && pricingMap.size > 0 && !hasDuplicateModelIds;
  const canCalculate = canSelectModels && selectedModelIds.length > 0;

  const calculatedBills = useMemo(() => {
    if (!hasCalculated || !confirmedUsage || !canCalculate) {
      return [];
    }
    return calculateMonthlyBills(confirmedUsage, selectedModelIds, pricingMap);
  }, [
    canCalculate,
    confirmedUsage,
    hasCalculated,
    pricingMap,
    selectedModelIds,
  ]);

  const selectedModelsTotalUsd = useMemo(
    () => calculateSelectedModelsTotal(calculatedBills),
    [calculatedBills],
  );

  const currentStep = confirmedUsage === null ? 0 : hasCalculated ? 2 : 1;

  const billingColumns: ColumnsType<ModelMonthlyBill> = [
    {
      title: "模型标识",
      dataIndex: "modelId",
      key: "modelId",
      render: (value: string) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: "输入费用",
      dataIndex: "inputCostUsd",
      key: "inputCostUsd",
      align: "right",
      render: (value: number) => formatUsd(value),
    },
    {
      title: "输出费用",
      dataIndex: "outputCostUsd",
      key: "outputCostUsd",
      align: "right",
      render: (value: number) => formatUsd(value),
    },
    {
      title: "缓存读费用",
      dataIndex: "cacheReadCostUsd",
      key: "cacheReadCostUsd",
      align: "right",
      render: (value: number) => formatUsd(value),
    },
    {
      title: "缓存写费用",
      dataIndex: "cacheWriteCostUsd",
      key: "cacheWriteCostUsd",
      align: "right",
      render: (value: number) => formatUsd(value),
    },
    {
      title: "总费用",
      dataIndex: "totalCostUsd",
      key: "totalCostUsd",
      align: "right",
      render: (value: number) => <Text strong>{formatUsd(value)}</Text>,
    },
  ];

  const updateUsage = (
    field: keyof MonthlyUsageData,
    nextValue: number | null,
  ) => {
    setUsageDraft((prev) => ({
      ...prev,
      [field]: normalizeNonNegativeInteger(nextValue),
    }));
    setConfirmedUsage(null);
    setHasCalculated(false);
  };

  const updatePricingRow = (
    rowId: number,
    field: keyof ModelPricingData,
    nextValue: string | number | null,
  ) => {
    setPricingRows((prev) =>
      prev.map((row) => {
        if (row.rowId !== rowId) return row;
        if (field === "modelId") {
          return { ...row, modelId: String(nextValue ?? "").trim() };
        }
        return {
          ...row,
          [field]: normalizeNonNegativeNumber(
            typeof nextValue === "number" ? nextValue : Number(nextValue ?? 0),
          ),
        };
      }),
    );
    setHasCalculated(false);
  };

  const addPricingRow = () => {
    setPricingRows((prev) => [...prev, createPricingRow(nextPricingRowId)]);
    setNextPricingRowId((prev) => prev + 1);
    setHasCalculated(false);
  };

  const removePricingRow = (rowId: number) => {
    setPricingRows((prev) => {
      if (prev.length <= 1) return prev;
      return prev.filter((row) => row.rowId !== rowId);
    });
    setHasCalculated(false);
  };

  const handleConfirmUsage = () => {
    if (!canConfirmUsage) return;
    setConfirmedUsage({ ...usageDraft });
    setHasCalculated(false);
  };

  const handleCalculate = () => {
    if (!canCalculate) return;
    setHasCalculated(true);
  };

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Title level={3} style={{ marginTop: 0 }}>
          大模型月度账单计算器（TypeScript Web UI）
        </Title>
        <Text type="secondary">
          流程固定：先输入用量数据，再选择 1
          个或多个模型，最后计算各模型分项费用。
        </Text>

        <Divider />

        <Steps
          current={currentStep}
          items={[
            { title: "输入用量数据" },
            { title: "选择模型" },
            { title: "查看账单明细" },
          ]}
          style={{ marginBottom: 24 }}
        />

        <Card
          title="步骤 1/2：输入月度用量数据（token）"
          size="small"
          style={{ marginBottom: 16 }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Text>输入 token 用量</Text>
              <InputNumber
                min={0}
                value={usageDraft.inputTokens}
                onChange={(value) => updateUsage("inputTokens", value)}
                style={{ width: "100%" }}
              />
            </Col>
            <Col xs={24} md={12}>
              <Text>输出 token 用量</Text>
              <InputNumber
                min={0}
                value={usageDraft.outputTokens}
                onChange={(value) => updateUsage("outputTokens", value)}
                style={{ width: "100%" }}
              />
            </Col>
            <Col xs={24} md={12}>
              <Text>缓存读 token 用量</Text>
              <InputNumber
                min={0}
                value={usageDraft.cacheReadTokens}
                onChange={(value) => updateUsage("cacheReadTokens", value)}
                style={{ width: "100%" }}
              />
            </Col>
            <Col xs={24} md={12}>
              <Text>缓存写 token 用量</Text>
              <InputNumber
                min={0}
                value={usageDraft.cacheWriteTokens}
                onChange={(value) => updateUsage("cacheWriteTokens", value)}
                style={{ width: "100%" }}
              />
            </Col>
          </Row>

          <Space style={{ marginTop: 16 }}>
            <Button
              type="primary"
              onClick={handleConfirmUsage}
              disabled={!canConfirmUsage}
            >
              确认用量并进入模型选择
            </Button>
            {confirmedUsage ? (
              <Tag color="success">已确认用量数据</Tag>
            ) : (
              <Tag color="default">尚未确认用量数据</Tag>
            )}
          </Space>
        </Card>

        <Card
          title="模型定价录入（手动）"
          size="small"
          style={{ marginBottom: 16 }}
        >
          <Space direction="vertical" style={{ width: "100%" }} size={12}>
            {pricingRows.map((row) => (
              <Card key={row.rowId} size="small">
                <Row gutter={[12, 12]} align="middle">
                  <Col xs={24} md={6}>
                    <Text>模型标识</Text>
                    <Input
                      value={row.modelId}
                      onChange={(event) =>
                        updatePricingRow(
                          row.rowId,
                          "modelId",
                          event.target.value,
                        )
                      }
                      placeholder="例如：gpt-4o-mini"
                    />
                  </Col>
                  <Col xs={24} md={4}>
                    <Text>输入单价 / 百万</Text>
                    <InputNumber
                      min={0}
                      value={row.inputPerMillionUsd}
                      onChange={(value) =>
                        updatePricingRow(row.rowId, "inputPerMillionUsd", value)
                      }
                      style={{ width: "100%" }}
                    />
                  </Col>
                  <Col xs={24} md={4}>
                    <Text>输出单价 / 百万</Text>
                    <InputNumber
                      min={0}
                      value={row.outputPerMillionUsd}
                      onChange={(value) =>
                        updatePricingRow(
                          row.rowId,
                          "outputPerMillionUsd",
                          value,
                        )
                      }
                      style={{ width: "100%" }}
                    />
                  </Col>
                  <Col xs={24} md={4}>
                    <Text>缓存读单价 / 百万</Text>
                    <InputNumber
                      min={0}
                      value={row.cacheReadPerMillionUsd}
                      onChange={(value) =>
                        updatePricingRow(
                          row.rowId,
                          "cacheReadPerMillionUsd",
                          value,
                        )
                      }
                      style={{ width: "100%" }}
                    />
                  </Col>
                  <Col xs={24} md={4}>
                    <Text>缓存写单价 / 百万</Text>
                    <InputNumber
                      min={0}
                      value={row.cacheWritePerMillionUsd}
                      onChange={(value) =>
                        updatePricingRow(
                          row.rowId,
                          "cacheWritePerMillionUsd",
                          value,
                        )
                      }
                      style={{ width: "100%" }}
                    />
                  </Col>
                  <Col xs={24} md={2}>
                    <Button
                      danger
                      type="text"
                      icon={<DeleteOutlined />}
                      onClick={() => removePricingRow(row.rowId)}
                      disabled={pricingRows.length <= 1}
                    />
                  </Col>
                </Row>
              </Card>
            ))}

            <Button icon={<PlusOutlined />} onClick={addPricingRow}>
              添加模型定价
            </Button>
          </Space>

          {hasDuplicateModelIds && (
            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              message={`存在重复模型标识：${duplicateModelIds.join("、")}`}
              showIcon
            />
          )}
        </Card>

        <Card title="步骤 2/2：选择模型并计算" size="small">
          <Space direction="vertical" style={{ width: "100%" }} size={12}>
            <Select
              mode="multiple"
              value={selectedModelIds}
              options={modelOptions}
              onChange={(values) => {
                setSelectedModelIds(values);
                setHasCalculated(false);
              }}
              placeholder="选择 1 个或多个模型"
              disabled={!canSelectModels}
              style={{ width: "100%" }}
            />

            <Button
              type="primary"
              onClick={handleCalculate}
              disabled={!canCalculate}
            >
              计算各类模型月度账单
            </Button>
          </Space>
        </Card>
      </Card>

      {hasCalculated && (
        <Card style={{ marginTop: 16 }} title="账单结果">
          <Table<ModelMonthlyBill>
            rowKey="modelId"
            columns={billingColumns}
            dataSource={calculatedBills}
            pagination={false}
          />
          <Divider />
          <Title level={4} style={{ marginBottom: 0, textAlign: "right" }}>
            所选模型总计：{formatUsd(selectedModelsTotalUsd)}
          </Title>
        </Card>
      )}
    </div>
  );
};
