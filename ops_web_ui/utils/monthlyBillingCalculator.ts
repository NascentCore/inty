/**
 * 大模型月度账单计算工具
 * CREATED_BY_AGENT
 *
 * 设计说明：
 * - 将“输入/输出/缓存读/缓存写”四类 token 用量与模型定价解耦
 * - 所有计算统一按“每百万 token 单价”转换为美元金额
 * - 对外提供纯函数，便于页面复用与 vitest 校验
 */

export const TOKENS_PER_MILLION = 1_000_000;

export interface MonthlyUsageData {
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens: number;
  cacheWriteTokens: number;
}

export interface ModelPricingData {
  modelId: string;
  inputPerMillionUsd: number;
  outputPerMillionUsd: number;
  cacheReadPerMillionUsd: number;
  cacheWritePerMillionUsd: number;
}

export interface ModelMonthlyBill {
  modelId: string;
  inputCostUsd: number;
  outputCostUsd: number;
  cacheReadCostUsd: number;
  cacheWriteCostUsd: number;
  totalCostUsd: number;
}

export const roundUsd = (value: number): number =>
  Math.round(value * 1_000_000) / 1_000_000;

export const isUsageDataValid = (usage: MonthlyUsageData): boolean =>
  usage.inputTokens >= 0 &&
  usage.outputTokens >= 0 &&
  usage.cacheReadTokens >= 0 &&
  usage.cacheWriteTokens >= 0;

export const findDuplicateModelIds = (
  pricings: ModelPricingData[],
): string[] => {
  const counts = new Map<string, number>();
  for (const pricing of pricings) {
    const modelId = pricing.modelId.trim();
    if (!modelId) continue;
    counts.set(modelId, (counts.get(modelId) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .filter(([, count]) => count > 1)
    .map(([modelId]) => modelId);
};

export const toPricingMap = (
  pricings: ModelPricingData[],
): Map<string, ModelPricingData> => {
  const duplicates = findDuplicateModelIds(pricings);
  if (duplicates.length > 0) {
    throw new Error(`模型标识重复: ${duplicates.join(", ")}`);
  }
  const map = new Map<string, ModelPricingData>();
  for (const pricing of pricings) {
    const modelId = pricing.modelId.trim();
    if (!modelId) continue;
    map.set(modelId, { ...pricing, modelId });
  }
  return map;
};

export const calculateModelBill = (
  usage: MonthlyUsageData,
  pricing: ModelPricingData,
): ModelMonthlyBill => {
  const inputCostUsd = roundUsd(
    (usage.inputTokens / TOKENS_PER_MILLION) * pricing.inputPerMillionUsd,
  );
  const outputCostUsd = roundUsd(
    (usage.outputTokens / TOKENS_PER_MILLION) * pricing.outputPerMillionUsd,
  );
  const cacheReadCostUsd = roundUsd(
    (usage.cacheReadTokens / TOKENS_PER_MILLION) *
      pricing.cacheReadPerMillionUsd,
  );
  const cacheWriteCostUsd = roundUsd(
    (usage.cacheWriteTokens / TOKENS_PER_MILLION) *
      pricing.cacheWritePerMillionUsd,
  );
  const totalCostUsd = roundUsd(
    inputCostUsd + outputCostUsd + cacheReadCostUsd + cacheWriteCostUsd,
  );
  return {
    modelId: pricing.modelId,
    inputCostUsd,
    outputCostUsd,
    cacheReadCostUsd,
    cacheWriteCostUsd,
    totalCostUsd,
  };
};

export const calculateMonthlyBills = (
  usage: MonthlyUsageData,
  selectedModelIds: string[],
  pricingMap: Map<string, ModelPricingData>,
): ModelMonthlyBill[] =>
  selectedModelIds.map((modelId) => {
    const pricing = pricingMap.get(modelId);
    if (!pricing) {
      throw new Error(`未找到模型定价: ${modelId}`);
    }
    return calculateModelBill(usage, pricing);
  });

export const calculateSelectedModelsTotal = (
  bills: ModelMonthlyBill[],
): number => roundUsd(bills.reduce((sum, bill) => sum + bill.totalCostUsd, 0));
