import { describe, expect, it } from "vitest";
import {
  calculateModelBill,
  calculateMonthlyBills,
  calculateSelectedModelsTotal,
  findDuplicateModelIds,
  isUsageDataValid,
  toPricingMap,
  type ModelPricingData,
  type MonthlyUsageData,
} from "../utils/monthlyBillingCalculator";

describe("monthlyBillingCalculator", () => {
  const usage: MonthlyUsageData = {
    inputTokens: 2_000_000,
    outputTokens: 1_000_000,
    cacheReadTokens: 500_000,
    cacheWriteTokens: 200_000,
  };

  it("校验用量数据必须为非负数", () => {
    expect(isUsageDataValid(usage)).toBe(true);
    expect(
      isUsageDataValid({
        ...usage,
        inputTokens: -1,
      }),
    ).toBe(false);
  });

  it("识别重复模型标识", () => {
    const duplicatePricings: ModelPricingData[] = [
      {
        modelId: "gpt-4o-mini",
        inputPerMillionUsd: 0.15,
        outputPerMillionUsd: 0.6,
        cacheReadPerMillionUsd: 0.075,
        cacheWritePerMillionUsd: 0.3,
      },
      {
        modelId: "gpt-4o-mini",
        inputPerMillionUsd: 0.2,
        outputPerMillionUsd: 0.7,
        cacheReadPerMillionUsd: 0.08,
        cacheWritePerMillionUsd: 0.35,
      },
    ];

    expect(findDuplicateModelIds(duplicatePricings)).toEqual(["gpt-4o-mini"]);
    expect(() => toPricingMap(duplicatePricings)).toThrow("模型标识重复");
  });

  it("按模型计算分项费用和总费用", () => {
    const pricing: ModelPricingData = {
      modelId: "gpt-4o-mini",
      inputPerMillionUsd: 0.15,
      outputPerMillionUsd: 0.6,
      cacheReadPerMillionUsd: 0.075,
      cacheWritePerMillionUsd: 0.3,
    };

    expect(calculateModelBill(usage, pricing)).toEqual({
      modelId: "gpt-4o-mini",
      inputCostUsd: 0.3,
      outputCostUsd: 0.6,
      cacheReadCostUsd: 0.0375,
      cacheWriteCostUsd: 0.06,
      totalCostUsd: 0.9975,
    });
  });

  it("支持一次选择多个模型并汇总", () => {
    const pricingMap = toPricingMap([
      {
        modelId: "gpt-4o-mini",
        inputPerMillionUsd: 0.15,
        outputPerMillionUsd: 0.6,
        cacheReadPerMillionUsd: 0.075,
        cacheWritePerMillionUsd: 0.3,
      },
      {
        modelId: "gemini-2.5-flash",
        inputPerMillionUsd: 0.1,
        outputPerMillionUsd: 0.4,
        cacheReadPerMillionUsd: 0.05,
        cacheWritePerMillionUsd: 0.2,
      },
    ]);

    const bills = calculateMonthlyBills(
      usage,
      ["gpt-4o-mini", "gemini-2.5-flash"],
      pricingMap,
    );
    expect(bills).toEqual([
      {
        modelId: "gpt-4o-mini",
        inputCostUsd: 0.3,
        outputCostUsd: 0.6,
        cacheReadCostUsd: 0.0375,
        cacheWriteCostUsd: 0.06,
        totalCostUsd: 0.9975,
      },
      {
        modelId: "gemini-2.5-flash",
        inputCostUsd: 0.2,
        outputCostUsd: 0.4,
        cacheReadCostUsd: 0.025,
        cacheWriteCostUsd: 0.04,
        totalCostUsd: 0.665,
      },
    ]);
    expect(calculateSelectedModelsTotal(bills)).toBe(1.6625);
  });
});
