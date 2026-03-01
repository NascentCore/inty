import type { ImageGenerationLatencyItem } from "../types";

export type PerformanceDateRangeType = "7" | "30" | "90" | "all";

export interface PerformanceDateRangeOption {
  value: PerformanceDateRangeType;
  label: string;
}

export const PERFORMANCE_DATE_RANGE_OPTIONS: PerformanceDateRangeOption[] = [
  { value: "7", label: "最近 7 天" },
  { value: "30", label: "最近 30 天" },
  { value: "90", label: "最近 90 天" },
  { value: "all", label: "全部" },
];

export const PERFORMANCE_MODEL_COLORS = [
  "#1890ff",
  "#52c41a",
  "#faad14",
  "#f5222d",
  "#722ed1",
  "#13c2c2",
];

export interface ImageGenerationLatencyByModel {
  model: string;
  color: string;
  items: ImageGenerationLatencyItem[];
}

export function buildPerformanceAnalyticsParams(
  dateRangeType: PerformanceDateRangeType,
): { activity_last_days?: number } {
  if (dateRangeType === "all") {
    return {};
  }
  return { activity_last_days: Number(dateRangeType) };
}

export function formatDurationFromSeconds(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(0)}秒`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}分${remainingSeconds.toFixed(0)}秒`;
}

export function groupImageGenerationLatencyByModel(
  items: ImageGenerationLatencyItem[],
): ImageGenerationLatencyByModel[] {
  const groupedItems = items.reduce(
    (accumulator, item) => {
      if (!accumulator[item.model]) {
        accumulator[item.model] = [];
      }
      accumulator[item.model].push(item);
      return accumulator;
    },
    {} as Record<string, ImageGenerationLatencyItem[]>,
  );

  return Object.entries(groupedItems).map(([model, modelItems], index) => ({
    model,
    color: PERFORMANCE_MODEL_COLORS[index % PERFORMANCE_MODEL_COLORS.length],
    items: modelItems,
  }));
}
