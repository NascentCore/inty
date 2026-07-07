import { describe, expect, it } from "vitest";
import type { ImageGenerationLatencyItem } from "../types";
import {
  buildPerformanceAnalyticsParams,
  formatDurationFromSeconds,
  groupImageGenerationLatencyByModel,
  PERFORMANCE_MODEL_COLORS,
} from "../utils/performanceAnalytics";

describe("buildPerformanceAnalyticsParams", () => {
  it("all 范围不带天数参数", () => {
    expect(buildPerformanceAnalyticsParams("all")).toEqual({});
  });

  it("最近 30 天带 activity_last_days", () => {
    expect(buildPerformanceAnalyticsParams("30")).toEqual({
      activity_last_days: 30,
    });
  });
});

describe("formatDurationFromSeconds", () => {
  it("分钟内展示秒数", () => {
    expect(formatDurationFromSeconds(41)).toBe("41秒");
  });

  it("超过 60 秒展示分秒", () => {
    expect(formatDurationFromSeconds(64)).toBe("1分4秒");
  });
});

describe("groupImageGenerationLatencyByModel", () => {
  it("按模型分组并分配颜色", () => {
    const items: ImageGenerationLatencyItem[] = [
      {
        hour: "2026-03-01 00:00:00",
        model: "gemini",
        avg_latency_ms: 1200,
        count: 2,
      },
      {
        hour: "2026-03-01 00:00:00",
        model: "fal",
        avg_latency_ms: 1800,
        count: 1,
      },
      {
        hour: "2026-03-01 01:00:00",
        model: "gemini",
        avg_latency_ms: 1000,
        count: 3,
      },
    ];

    const grouped = groupImageGenerationLatencyByModel(items);

    expect(grouped).toHaveLength(2);
    expect(grouped[0]).toEqual({
      model: "gemini",
      color: PERFORMANCE_MODEL_COLORS[0],
      items: [items[0], items[2]],
    });
    expect(grouped[1]).toEqual({
      model: "fal",
      color: PERFORMANCE_MODEL_COLORS[1],
      items: [items[1]],
    });
  });
});
