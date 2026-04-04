/**
 * CREATED_BY_AGENT
 */
import type {
  DailyVoiceAudiosResponse,
  UserAnalyticsReportItem,
  UserAnalyticsReportDailyTopAgentItem,
  UserAnalyticsStatsResponse,
  VoiceAudioGroupByUserAgent,
} from "../types";

type DailyUsageAxis = "y" | "y2";

interface UsageMetricConfig<
  MetricKey extends keyof UserAnalyticsStatsResponse =
    keyof UserAnalyticsStatsResponse,
> {
  key: MetricKey;
  label: string;
  color: string;
  axis: DailyUsageAxis;
}

export const DAILY_USAGE_CHART_METRICS = [
  {
    key: "total_user_messages",
    label: "消息数",
    color: "#1677ff",
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
  {
    key: "avg_messages_per_user",
    label: "人均消息数",
    color: "#2f54eb",
    axis: "y2",
  },
] as const satisfies ReadonlyArray<UsageMetricConfig>;

const DAILY_USAGE_RATIO_SUPPORT_METRICS = [
  {
    key: "total_image_generation_requests",
    label: "生图请求数(比值计算)",
    color: "#52c41a",
    axis: "y",
  },
  {
    key: "total_ai_messages",
    label: "AI回复消息数(比值计算)",
    color: "#fa541c",
    axis: "y",
  },
] as const satisfies ReadonlyArray<UsageMetricConfig>;

const DAILY_USAGE_SERIES_METRICS = [
  ...DAILY_USAGE_CHART_METRICS,
  ...DAILY_USAGE_RATIO_SUPPORT_METRICS,
] as const;

export const DAILY_IMAGE_USAGE_CHART_METRICS = [
  {
    key: "total_image_generation_requests",
    label: "生图请求数",
    color: "#52c41a",
    axis: "y",
  },
  {
    key: "total_image_generation_success",
    label: "生图成功数",
    color: "#1677ff",
    axis: "y",
  },
  {
    key: "image_generation_success_rate",
    label: "生图成功率",
    color: "#faad14",
    axis: "y2",
  },
] as const satisfies ReadonlyArray<UsageMetricConfig>;

export const DAILY_USAGE_METRICS = DAILY_USAGE_CHART_METRICS.filter(
  (metric) => metric.axis === "y",
);
export const DAILY_USAGE_HAS_SECONDARY_AXIS = DAILY_USAGE_CHART_METRICS.some(
  (metric) => metric.axis === "y2",
);
export const DAILY_USAGE_SECONDARY_AXIS_TITLE =
  DAILY_USAGE_CHART_METRICS.filter((metric) => metric.axis === "y2")
    .map((metric) => metric.label)
    .join(" / ");
export const DAILY_USAGE_SECONDARY_AXIS_COLOR =
  DAILY_USAGE_CHART_METRICS.find((metric) => metric.axis === "y2")?.color ??
  "#ff4d4f";
export const DAILY_USAGE_VOICE_MESSAGE_RATIO_LABEL = "语音播报次数 / 消息数";
export const DAILY_USAGE_VOICE_MESSAGE_RATIO_COLOR = "#13c2c2";
export const DAILY_USAGE_IMAGE_AI_REPLY_RATIO_LABEL =
  "生图请求数 / AI回复消息数";
export const DAILY_USAGE_IMAGE_AI_REPLY_RATIO_COLOR = "#52c41a";
export const DAILY_IMAGE_USAGE_HAS_SECONDARY_AXIS =
  DAILY_IMAGE_USAGE_CHART_METRICS.some((metric) => metric.axis === "y2");
export const DAILY_IMAGE_USAGE_SECONDARY_AXIS_TITLE =
  DAILY_IMAGE_USAGE_CHART_METRICS.filter((metric) => metric.axis === "y2")
    .map((metric) => metric.label)
    .join(" / ");
export const DAILY_IMAGE_USAGE_SECONDARY_AXIS_COLOR =
  DAILY_IMAGE_USAGE_CHART_METRICS.find((metric) => metric.axis === "y2")
    ?.color ?? "#faad14";

const removeFirstAudioInVoiceMessageGroup = (
  group: VoiceAudioGroupByUserAgent,
): VoiceAudioGroupByUserAgent => ({
  ...group,
  audios: group.audios.slice(1),
});

export const removeOpeningVoiceMessageAudios = (
  dailyVoiceAudios: DailyVoiceAudiosResponse,
): DailyVoiceAudiosResponse => ({
  ...dailyVoiceAudios,
  voice_message_audios: dailyVoiceAudios.voice_message_audios
    .map(removeFirstAudioInVoiceMessageGroup)
    .filter((group) => group.audios.length > 0),
});

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
  (typeof DAILY_USAGE_SERIES_METRICS)[number]["key"];

export type DailyImageUsageMetricKey =
  (typeof DAILY_IMAGE_USAGE_CHART_METRICS)[number]["key"];

interface UsageSeries<MetricKey extends keyof UserAnalyticsStatsResponse> {
  dates: string[];
  valuesByMetric: Record<MetricKey, number[]>;
}

export interface DailyUsageSeries extends UsageSeries<DailyUsageMetricKey> {}
export interface DailyImageUsageSeries extends UsageSeries<DailyImageUsageMetricKey> {}
export interface DailyTopAgentPoint {
  date: string;
  rank: number;
  agent_name: string;
  total_rounds: number;
  user_count: number;
}
export interface DailyTopAgentTrendLine {
  agent_name: string;
  points: DailyTopAgentPoint[];
}
export interface DailyTopAgentsTrendSeries {
  dates: string[];
  dailyTopAgentsByDate: Record<string, DailyTopAgentPoint[]>;
  lines: DailyTopAgentTrendLine[];
}

export const WEEKLY_USAGE_ROLLING_WINDOW_DAYS = 7;
export const DAILY_TOP_AGENTS_LIMIT = 10;

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

const toImageGenerationSuccessRate = (
  totalImageGenerationSuccess: number,
  totalImageGenerationRequests: number,
): number => {
  if (totalImageGenerationRequests <= 0) {
    return 0;
  }
  return (totalImageGenerationSuccess / totalImageGenerationRequests) * 100;
};

const withImageGenerationSuccessRate = (
  series: DailyImageUsageSeries | null,
): DailyImageUsageSeries | null => {
  if (!series) {
    return null;
  }
  const requestValues = series.valuesByMetric.total_image_generation_requests;
  const successValues = series.valuesByMetric.total_image_generation_success;
  const imageGenerationSuccessRateValues = successValues.map(
    (successValue, index) =>
      toImageGenerationSuccessRate(successValue, requestValues[index] ?? 0),
  );
  return {
    ...series,
    valuesByMetric: {
      ...series.valuesByMetric,
      image_generation_success_rate: imageGenerationSuccessRateValues,
    },
  };
};

const buildMetricValuesByMetricKey = <
  MetricKey extends keyof UserAnalyticsStatsResponse,
>(
  dailyReports: UserAnalyticsReportItem[],
  metrics: ReadonlyArray<UsageMetricConfig<MetricKey>>,
  mapValues: (dailyValues: number[]) => number[],
): Record<MetricKey, number[]> => {
  const valuesByMetric = {} as Record<MetricKey, number[]>;
  metrics.forEach((metric) => {
    const dailyValues = dailyReports.map((report) =>
      toStatsMetricValue(report, metric.key),
    );
    valuesByMetric[metric.key] = mapValues(dailyValues);
  });
  return valuesByMetric;
};

const buildUsageSeries = <MetricKey extends keyof UserAnalyticsStatsResponse>(
  reports: UserAnalyticsReportItem[],
  metrics: ReadonlyArray<UsageMetricConfig<MetricKey>>,
  mapValues: (dailyValues: number[]) => number[],
): UsageSeries<MetricKey> | null => {
  const dailyReports = getSortedDailyReports(reports);
  if (dailyReports.length === 0) {
    return null;
  }

  const dates = dailyReports.map((report) => report.report_date);
  const valuesByMetric = buildMetricValuesByMetricKey(
    dailyReports,
    metrics,
    mapValues,
  );
  return { dates, valuesByMetric };
};

export const buildDailyUsageSeries = (
  reports: UserAnalyticsReportItem[],
): DailyUsageSeries | null => {
  return buildUsageSeries(
    reports,
    DAILY_USAGE_SERIES_METRICS,
    (dailyValues) => dailyValues,
  );
};

export const buildRollingDailyUsageSeries = (
  reports: UserAnalyticsReportItem[],
  windowDays: number = WEEKLY_USAGE_ROLLING_WINDOW_DAYS,
): DailyUsageSeries | null => {
  const normalizedWindowDays = Math.max(1, Math.floor(windowDays));
  return buildUsageSeries(reports, DAILY_USAGE_SERIES_METRICS, (values) =>
    buildRollingSums(values, normalizedWindowDays),
  );
};

const toVoiceRequestsPerMessageRatio = (
  totalVoiceRequests: number,
  totalAiMessages: number,
): number => {
  if (totalAiMessages <= 0) {
    return 0;
  }
  return totalVoiceRequests / totalAiMessages;
};

const toImageRequestsPerAiMessageRatio = (
  totalImageGenerationRequests: number,
  totalAiMessages: number,
): number => {
  if (totalAiMessages <= 0) {
    return 0;
  }
  return totalImageGenerationRequests / totalAiMessages;
};

export const buildVoiceRequestsPerMessageRatioValues = (
  usageSeries: DailyUsageSeries | null,
): number[] => {
  if (!usageSeries) {
    return [];
  }
  const totalVoiceRequestsValues =
    usageSeries.valuesByMetric.total_voice_requests;
  const totalAiMessagesValues = usageSeries.valuesByMetric.total_ai_messages;
  return totalVoiceRequestsValues.map((voiceRequests, index) =>
    toVoiceRequestsPerMessageRatio(
      voiceRequests,
      totalAiMessagesValues[index] ?? 0,
    ),
  );
};

export const buildImageRequestsPerAiMessageRatioValues = (
  usageSeries: DailyUsageSeries | null,
): number[] => {
  if (!usageSeries) {
    return [];
  }
  const totalImageGenerationRequestsValues =
    usageSeries.valuesByMetric.total_image_generation_requests;
  const totalAiMessagesValues = usageSeries.valuesByMetric.total_ai_messages;
  return totalImageGenerationRequestsValues.map((imageRequests, index) =>
    toImageRequestsPerAiMessageRatio(
      imageRequests,
      totalAiMessagesValues[index] ?? 0,
    ),
  );
};

export const buildDailyImageUsageSeries = (
  reports: UserAnalyticsReportItem[],
): DailyImageUsageSeries | null =>
  withImageGenerationSuccessRate(
    buildUsageSeries(
      reports,
      DAILY_IMAGE_USAGE_CHART_METRICS,
      (dailyValues) => dailyValues,
    ),
  );

export const buildRollingDailyImageUsageSeries = (
  reports: UserAnalyticsReportItem[],
  windowDays: number = WEEKLY_USAGE_ROLLING_WINDOW_DAYS,
): DailyImageUsageSeries | null => {
  const normalizedWindowDays = Math.max(1, Math.floor(windowDays));
  return withImageGenerationSuccessRate(
    buildUsageSeries(reports, DAILY_IMAGE_USAGE_CHART_METRICS, (values) =>
      buildRollingSums(values, normalizedWindowDays),
    ),
  );
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

const toFiniteNumber = (value: unknown): number => {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : 0;
};

const normalizeDailyTopAgents = (
  reportDate: string,
  dailyTopAgents: UserAnalyticsReportDailyTopAgentItem[],
  topN: number,
): DailyTopAgentPoint[] => {
  const normalizedAgents = dailyTopAgents
    .filter(
      (item) =>
        Boolean(item) &&
        typeof item.agent_name === "string" &&
        item.agent_name.length > 0,
    )
    .map((item, index) => ({
      date: reportDate,
      rank: Math.max(1, Math.floor(toFiniteNumber(item.rank) || index + 1)),
      agent_name: item.agent_name,
      total_rounds: Math.max(0, Math.floor(toFiniteNumber(item.total_rounds))),
      user_count: Math.max(0, Math.floor(toFiniteNumber(item.user_count))),
    }))
    .sort((a, b) => {
      if (a.rank !== b.rank) {
        return a.rank - b.rank;
      }
      if (a.total_rounds !== b.total_rounds) {
        return b.total_rounds - a.total_rounds;
      }
      return a.agent_name.localeCompare(b.agent_name);
    })
    .slice(0, topN);

  return normalizedAgents.map((item, index) => ({
    ...item,
    rank: index + 1,
  }));
};

export const buildDailyTopAgentsTrendSeries = (
  reports: UserAnalyticsReportItem[],
  topN: number = DAILY_TOP_AGENTS_LIMIT,
): DailyTopAgentsTrendSeries | null => {
  const normalizedTopN = Math.max(1, Math.floor(topN));
  const dailyReports = getSortedDailyReports(reports);
  if (dailyReports.length === 0) {
    return null;
  }

  const dates: string[] = [];
  const dailyTopAgentsByDate: Record<string, DailyTopAgentPoint[]> = {};
  const pointsByAgent = new Map<string, DailyTopAgentPoint[]>();

  dailyReports.forEach((report) => {
    const points = normalizeDailyTopAgents(
      report.report_date,
      report.daily_top_agents_by_rounds ?? [],
      normalizedTopN,
    );
    if (points.length === 0) {
      return;
    }
    dates.push(report.report_date);
    dailyTopAgentsByDate[report.report_date] = points;
    points.forEach((point) => {
      const existingPoints = pointsByAgent.get(point.agent_name) ?? [];
      existingPoints.push(point);
      pointsByAgent.set(point.agent_name, existingPoints);
    });
  });

  if (dates.length === 0) {
    return null;
  }

  const lines = Array.from(pointsByAgent.entries())
    .map(([agent_name, points]) => ({
      agent_name,
      points: points.slice().sort((a, b) => a.date.localeCompare(b.date)),
    }))
    .sort((a, b) => {
      const aRank = a.points[0]?.rank ?? Number.MAX_SAFE_INTEGER;
      const bRank = b.points[0]?.rank ?? Number.MAX_SAFE_INTEGER;
      if (aRank !== bRank) {
        return aRank - bRank;
      }
      return a.agent_name.localeCompare(b.agent_name);
    });

  return {
    dates,
    dailyTopAgentsByDate,
    lines,
  };
};
