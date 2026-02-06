/**
 * CREATED_BY_AGENT
 */
import type {
  UserAnalyticsReportItem,
  UserAnalyticsStatsResponse,
} from "../types";

export const DAILY_USAGE_METRICS = [
  { key: "total_user_messages", label: "消息数", color: "#1677ff" },
  { key: "total_image_generation_requests", label: "生图请求数", color: "#52c41a" },
  { key: "total_live_chat_sessions", label: "语音通话次数", color: "#faad14" },
  { key: "total_voice_requests", label: "语音播报次数", color: "#722ed1" },
] as const satisfies ReadonlyArray<{
  key: keyof UserAnalyticsStatsResponse;
  label: string;
  color: string;
}>;

export type DailyUsageMetricKey = (typeof DAILY_USAGE_METRICS)[number]["key"];

export interface DailyUsageSeries {
  dates: string[];
  valuesByMetric: Record<DailyUsageMetricKey, number[]>;
}

export const buildDailyUsageSeries = (
  reports: UserAnalyticsReportItem[],
): DailyUsageSeries | null => {
  const dailyReports = reports
    .filter((report) => report.report_type === "daily")
    .slice()
    .sort((a, b) => a.report_date.localeCompare(b.report_date));

  if (dailyReports.length === 0) {
    return null;
  }

  const dates = dailyReports.map((report) => report.report_date);
  const valuesByMetric = DAILY_USAGE_METRICS.reduce(
    (acc, metric) => {
      acc[metric.key] = dailyReports.map(
        (report) => report.stats[metric.key] ?? 0,
      );
      return acc;
    },
    {} as Record<DailyUsageMetricKey, number[]>,
  );

  return { dates, valuesByMetric };
};
