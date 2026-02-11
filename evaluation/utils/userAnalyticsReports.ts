/**
 * CREATED_BY_AGENT
 */
import type {
  UserAnalyticsReportItem,
  UserAnalyticsStatsResponse,
} from "../types";

type DailyUsageAxis = "y" | "y2";

export const DAILY_USAGE_CHART_METRICS = [
  {
    key: "total_user_messages",
    label: "消息数",
    color: "#1677ff",
    axis: "y",
  },
  {
    key: "total_image_generation_requests",
    label: "生图请求数",
    color: "#52c41a",
    axis: "y",
  },
  {
    key: "total_live_chat_sessions",
    label: "语音通话次数",
    color: "#faad14",
    axis: "y",
  },
  {
    key: "total_voice_requests",
    label: "语音播报次数",
    color: "#722ed1",
    axis: "y",
  },
  {
    key: "total_chat_initiators",
    label: "发起聊天的人数",
    color: "#ff4d4f",
    axis: "y2",
  },
] as const satisfies ReadonlyArray<{
  key: keyof UserAnalyticsStatsResponse;
  label: string;
  color: string;
  axis: DailyUsageAxis;
}>;

export const DAILY_USAGE_METRICS = DAILY_USAGE_CHART_METRICS.filter(
  (metric) => metric.axis === "y",
);
export const DAILY_USAGE_HAS_SECONDARY_AXIS = DAILY_USAGE_CHART_METRICS.some(
  (metric) => metric.axis === "y2",
);
export const DAILY_USAGE_SECONDARY_AXIS_TITLE = DAILY_USAGE_CHART_METRICS
  .filter((metric) => metric.axis === "y2")
  .map((metric) => metric.label)
  .join(" / ");
export const DAILY_USAGE_SECONDARY_AXIS_COLOR =
  DAILY_USAGE_CHART_METRICS.find((metric) => metric.axis === "y2")?.color ??
  "#ff4d4f";

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

export type DailyUsageMetricKey =
  (typeof DAILY_USAGE_CHART_METRICS)[number]["key"];

export interface DailyUsageSeries {
  dates: string[];
  valuesByMetric: Record<DailyUsageMetricKey, number[]>;
}

export const WEEKLY_USAGE_ROLLING_WINDOW_DAYS = 7;

const getSortedDailyReports = (
  reports: UserAnalyticsReportItem[],
): UserAnalyticsReportItem[] =>
  reports
    .filter((report) => report.report_type === "daily")
    .slice()
    .sort((a, b) => a.report_date.localeCompare(b.report_date));

const toStatsMetricValue = (
  report: UserAnalyticsReportItem,
  metricKey: keyof UserAnalyticsStatsResponse,
): number => {
  const rawValue = Number(report.stats[metricKey] ?? 0);
  return Number.isFinite(rawValue) ? rawValue : 0;
};

const buildRollingSums = (values: number[], windowDays: number): number[] => {
  const rollingSums: number[] = [];
  let runningSum = 0;
  values.forEach((value, index) => {
    runningSum += value;
    if (index >= windowDays) {
      runningSum -= values[index - windowDays];
    }
    rollingSums.push(runningSum);
  });
  return rollingSums;
};

const buildMetricValuesByMetricKey = (
  dailyReports: UserAnalyticsReportItem[],
  mapValues: (dailyValues: number[]) => number[],
): Record<DailyUsageMetricKey, number[]> =>
  DAILY_USAGE_CHART_METRICS.reduce(
    (acc, metric) => {
      const dailyValues = dailyReports.map((report) =>
        toStatsMetricValue(report, metric.key),
      );
      acc[metric.key] = mapValues(dailyValues);
      return acc;
    },
    {} as Record<DailyUsageMetricKey, number[]>,
  );

export const buildDailyUsageSeries = (
  reports: UserAnalyticsReportItem[],
): DailyUsageSeries | null => {
  const dailyReports = getSortedDailyReports(reports);

  if (dailyReports.length === 0) {
    return null;
  }

  const dates = dailyReports.map((report) => report.report_date);
  const valuesByMetric = buildMetricValuesByMetricKey(
    dailyReports,
    (dailyValues) => dailyValues,
  );

  return { dates, valuesByMetric };
};

export const buildRollingDailyUsageSeries = (
  reports: UserAnalyticsReportItem[],
  windowDays: number = WEEKLY_USAGE_ROLLING_WINDOW_DAYS,
): DailyUsageSeries | null => {
  const dailyReports = getSortedDailyReports(reports);
  if (dailyReports.length === 0) {
    return null;
  }

  const normalizedWindowDays = Math.max(1, Math.floor(windowDays));
  const dates = dailyReports.map((report) => report.report_date);
  const valuesByMetric = buildMetricValuesByMetricKey(dailyReports, (values) =>
    buildRollingSums(values, normalizedWindowDays),
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
