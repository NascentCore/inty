/**
 * CREATED_BY_AGENT
 */
import type {
  UserAnalyticsReportItem,
  UserAnalyticsStatsResponse,
} from "../types";

export const DAILY_USAGE_METRICS = [
  { key: "total_user_messages", label: "消息数", color: "#1677ff" },
  {
    key: "total_image_generation_requests",
    label: "生图请求数",
    color: "#52c41a",
  },
  { key: "total_live_chat_sessions", label: "语音通话次数", color: "#faad14" },
  { key: "total_voice_requests", label: "语音播报次数", color: "#722ed1" },
] as const satisfies ReadonlyArray<{
  key: keyof UserAnalyticsStatsResponse;
  label: string;
  color: string;
}>;

const ISO_DATE_REGEX = /^(\d{4})-(\d{2})-(\d{2})$/;
const WEEKDAY_LABELS = [
  "周7",
  "周1",
  "周2",
  "周3",
  "周4",
  "周5",
  "周6",
] as const;

const toValidUtcDate = (
  year: number,
  month: number,
  day: number,
): Date | null => {
  const utcTime = Date.UTC(year, month - 1, day);
  if (Number.isNaN(utcTime)) {
    return null;
  }
  const dateValue = new Date(utcTime);
  if (
    dateValue.getUTCFullYear() !== year ||
    dateValue.getUTCMonth() !== month - 1 ||
    dateValue.getUTCDate() !== day
  ) {
    return null;
  }
  return dateValue;
};

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

const formatDateWithWeekday = (date: string): string => {
  const match = ISO_DATE_REGEX.exec(date);
  if (!match) {
    return date;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const dateValue = toValidUtcDate(year, month, day);
  if (!dateValue) {
    return date;
  }
  const weekdayLabel = WEEKDAY_LABELS[dateValue.getUTCDay()] ?? "";
  if (!weekdayLabel) {
    return date;
  }
  return `${date}\n${weekdayLabel}`;
};

export const buildDailyUsageTickText = (dates: string[]): string[] =>
  dates.map(formatDateWithWeekday);

export const sortReportsByDateDesc = (
  reports: UserAnalyticsReportItem[],
): UserAnalyticsReportItem[] =>
  reports.slice().sort((a, b) => b.report_date.localeCompare(a.report_date));
