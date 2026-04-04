/**
 * CREATED_BY_AGENT
 */
import { describe, it, expect } from "vitest";
import {
  buildDailyUsageSeries,
  buildDailyImageUsageSeries,
  buildDailyTopAgentsTrendSeries,
  buildRollingDailyUsageSeries,
  buildRollingDailyImageUsageSeries,
  buildImageRequestsPerAiMessageRatioValues,
  buildVoiceRequestsPerMessageRatioValues,
  buildDailyUsageTickText,
  removeOpeningVoiceMessageAudios,
  sortReportsByDateDesc,
  DAILY_TOP_AGENTS_LIMIT,
  WEEKLY_USAGE_ROLLING_WINDOW_DAYS,
} from "../utils/userAnalyticsReports";
import type {
  DailyVoiceAudiosResponse,
  UserAnalyticsReportItem,
  UserAnalyticsStatsResponse,
} from "../types";

const buildStats = (
  overrides: Partial<UserAnalyticsStatsResponse> = {},
): UserAnalyticsStatsResponse => ({
  total_new_users: 0,
  total_chat_initiators: 0,
  total_user_messages: 0,
  total_ai_messages: 0,
  total_active_sessions: 0,
  total_voice_requests: 0,
  avg_messages_per_user: 0,
  avg_sessions_per_user: 0,
  avg_voice_requests_per_user: 0,
  avg_rounds_per_session: 0,
  new_user_open_rate: 0,
  total_image_generation_requests: 0,
  total_image_generation_success: 0,
  total_image_generation_failures: 0,
  image_generation_success_rate: 0,
  total_image_new_generation: 0,
  total_image_fallback_used: 0,
  total_live_chat_users: 0,
  total_live_chat_sessions: 0,
  total_live_chat_duration: 0,
  avg_live_chat_sessions_per_user: 0,
  avg_live_chat_duration_per_user: 0,
  avg_live_chat_duration_per_session: 0,
  ...overrides,
});

const buildReport = (
  overrides: Partial<UserAnalyticsReportItem>,
): UserAnalyticsReportItem => ({
  id: overrides.id ?? "report",
  report_type: overrides.report_type ?? "daily",
  report_date: overrides.report_date ?? "2026-02-01",
  stats: overrides.stats ?? buildStats(),
  daily_top_agents_by_rounds: overrides.daily_top_agents_by_rounds ?? [],
  daily_most_discussed_agent: overrides.daily_most_discussed_agent ?? null,
  charts: overrides.charts ?? null,
  created_at: overrides.created_at ?? null,
});

describe("buildDailyUsageSeries", () => {
  it("过滤周报并按日期升序输出", () => {
    const reports = [
      buildReport({
        id: "r2",
        report_date: "2026-02-02",
        stats: buildStats({
          total_chat_initiators: 5,
          total_user_messages: 20,
          avg_messages_per_user: 4,
          total_image_generation_requests: 4,
          total_live_chat_sessions: 2,
          total_voice_requests: 1,
        }),
      }),
      buildReport({
        id: "r1",
        report_date: "2026-02-01",
        stats: buildStats({
          total_chat_initiators: 3,
          total_user_messages: 10,
          avg_messages_per_user: 2.5,
          total_image_generation_requests: 2,
          total_live_chat_sessions: 1,
          total_voice_requests: 0,
        }),
      }),
      buildReport({
        id: "w1",
        report_type: "weekly",
        report_date: "2026-W05",
        stats: buildStats({ total_user_messages: 999 }),
      }),
    ];

    const series = buildDailyUsageSeries(reports);

    expect(series?.dates).toEqual(["2026-02-01", "2026-02-02"]);
    expect(series?.valuesByMetric.total_user_messages).toEqual([10, 20]);
    expect(series?.valuesByMetric.total_live_chat_sessions).toEqual([1, 2]);
    expect(series?.valuesByMetric.total_voice_requests).toEqual([0, 1]);
    expect(series?.valuesByMetric.total_chat_initiators).toEqual([3, 5]);
    expect(series?.valuesByMetric.avg_messages_per_user).toEqual([2.5, 4]);
  });

  it("没有日报数据时返回空值", () => {
    const series = buildDailyUsageSeries([
      buildReport({ report_type: "weekly", report_date: "2026-W05" }),
    ]);
    expect(series).toBeNull();
  });

  it("空列表时返回空值", () => {
    const series = buildDailyUsageSeries([]);
    expect(series).toBeNull();
  });
});

describe("buildDailyImageUsageSeries", () => {
  it("按日期升序输出生图请求、成功与成功率曲线，并过滤周报", () => {
    const reports = [
      buildReport({
        id: "r2",
        report_date: "2026-02-02",
        stats: buildStats({
          total_image_generation_requests: 12,
          total_image_generation_success: 9,
          image_generation_success_rate: 99,
        }),
      }),
      buildReport({
        id: "r1",
        report_date: "2026-02-01",
        stats: buildStats({
          total_image_generation_requests: 8,
          total_image_generation_success: 6,
          image_generation_success_rate: 1,
        }),
      }),
      buildReport({
        id: "w1",
        report_type: "weekly",
        report_date: "2026-W05",
        stats: buildStats({
          total_image_generation_requests: 999,
          total_image_generation_success: 999,
        }),
      }),
    ];

    const series = buildDailyImageUsageSeries(reports);

    expect(series?.dates).toEqual(["2026-02-01", "2026-02-02"]);
    expect(series?.valuesByMetric.total_image_generation_requests).toEqual([
      8, 12,
    ]);
    expect(series?.valuesByMetric.total_image_generation_success).toEqual([
      6, 9,
    ]);
    expect(series?.valuesByMetric.image_generation_success_rate).toEqual([
      75, 75,
    ]);
  });

  it("没有日报数据时返回空值", () => {
    const series = buildDailyImageUsageSeries([
      buildReport({ report_type: "weekly", report_date: "2026-W05" }),
    ]);
    expect(series).toBeNull();
  });
});

describe("buildRollingDailyUsageSeries", () => {
  it("按日期输出每日近7天滚动和", () => {
    const reports = Array.from({ length: 8 }, (_, index) => {
      const day = String(index + 1).padStart(2, "0");
      const value = index + 1;
      return buildReport({
        id: `r${value}`,
        report_date: `2026-02-${day}`,
        stats: buildStats({
          total_chat_initiators: value * 5,
          total_user_messages: value,
          avg_messages_per_user: value * 2,
          total_image_generation_requests: value * 2,
          total_live_chat_sessions: value * 3,
          total_voice_requests: value * 4,
        }),
      });
    });

    const series = buildRollingDailyUsageSeries(reports);

    expect(series?.valuesByMetric.total_user_messages).toEqual([
      1, 3, 6, 10, 15, 21, 28, 35,
    ]);
    expect(series?.valuesByMetric.total_voice_requests).toEqual([
      4, 12, 24, 40, 60, 84, 112, 140,
    ]);
    expect(series?.valuesByMetric.total_chat_initiators).toEqual([
      5, 15, 30, 50, 75, 105, 140, 175,
    ]);
    expect(series?.valuesByMetric.avg_messages_per_user).toEqual([
      2, 6, 12, 20, 30, 42, 56, 70,
    ]);
    expect(series?.dates[series.dates.length - 1]).toBe("2026-02-08");
    expect(WEEKLY_USAGE_ROLLING_WINDOW_DAYS).toBe(7);
  });

  it("支持自定义窗口并过滤周报", () => {
    const reports = [
      buildReport({
        id: "d1",
        report_date: "2026-02-01",
        stats: buildStats({
          total_user_messages: 10,
          total_chat_initiators: 2,
          avg_messages_per_user: 1,
        }),
      }),
      buildReport({
        id: "d2",
        report_date: "2026-02-02",
        stats: buildStats({
          total_user_messages: 20,
          total_chat_initiators: 4,
          avg_messages_per_user: 2,
        }),
      }),
      buildReport({
        id: "d3",
        report_date: "2026-02-03",
        stats: buildStats({
          total_user_messages: 30,
          total_chat_initiators: 6,
          avg_messages_per_user: 3,
        }),
      }),
      buildReport({
        id: "w1",
        report_type: "weekly",
        report_date: "2026-W05",
        stats: buildStats({ total_user_messages: 999 }),
      }),
    ];

    const series = buildRollingDailyUsageSeries(reports, 2);

    expect(series?.dates).toEqual(["2026-02-01", "2026-02-02", "2026-02-03"]);
    expect(series?.valuesByMetric.total_user_messages).toEqual([10, 30, 50]);
    expect(series?.valuesByMetric.total_chat_initiators).toEqual([2, 6, 10]);
    expect(series?.valuesByMetric.avg_messages_per_user).toEqual([1, 3, 5]);
  });

  it("没有日报数据时返回空值", () => {
    const series = buildRollingDailyUsageSeries([
      buildReport({ report_type: "weekly", report_date: "2026-W05" }),
    ]);
    expect(series).toBeNull();
  });
});

describe("buildVoiceRequestsPerMessageRatioValues", () => {
  it("按日期输出语音播报次数 / AI回复消息数比值，分母为 0 时返回 0", () => {
    const reports = [
      buildReport({
        id: "r2",
        report_date: "2026-02-02",
        stats: buildStats({
          total_ai_messages: 20,
          total_voice_requests: 10,
        }),
      }),
      buildReport({
        id: "r1",
        report_date: "2026-02-01",
        stats: buildStats({
          total_ai_messages: 0,
          total_voice_requests: 5,
        }),
      }),
    ];

    const usageSeries = buildDailyUsageSeries(reports);
    const ratioValues = buildVoiceRequestsPerMessageRatioValues(usageSeries);

    expect(ratioValues).toHaveLength(2);
    expect(ratioValues[0]).toBe(0);
    expect(ratioValues[1] ?? 0).toBeCloseTo(0.5, 6);
  });

  it("无用量序列时返回空数组", () => {
    expect(buildVoiceRequestsPerMessageRatioValues(null)).toEqual([]);
  });
});

describe("buildImageRequestsPerAiMessageRatioValues", () => {
  it("按日期输出生图请求数 / AI回复消息数比值，分母为 0 时返回 0", () => {
    const reports = [
      buildReport({
        id: "r2",
        report_date: "2026-02-02",
        stats: buildStats({
          total_image_generation_requests: 8,
          total_ai_messages: 20,
        }),
      }),
      buildReport({
        id: "r1",
        report_date: "2026-02-01",
        stats: buildStats({
          total_image_generation_requests: 5,
          total_ai_messages: 0,
        }),
      }),
    ];

    const usageSeries = buildDailyUsageSeries(reports);
    const ratioValues = buildImageRequestsPerAiMessageRatioValues(usageSeries);

    expect(ratioValues).toHaveLength(2);
    expect(ratioValues[0]).toBe(0);
    expect(ratioValues[1] ?? 0).toBeCloseTo(0.4, 6);
  });

  it("无用量序列时返回空数组", () => {
    expect(buildImageRequestsPerAiMessageRatioValues(null)).toEqual([]);
  });
});

describe("removeOpeningVoiceMessageAudios", () => {
  it("按用户-角色分组去掉首条语音播报，并清理空分组", () => {
    const voiceAudios: DailyVoiceAudiosResponse = {
      voice_message_audios: [
        {
          user_id: "u1",
          agent_id: "a1",
          agent_name: "A",
          audios: [
            {
              audio_url: "https://example.com/opening-u1-a1.mp3",
              message_id: 1,
              created_at: "2026-02-01T00:00:00Z",
              duration_seconds: 3.8,
            },
            {
              audio_url: "https://example.com/reply-u1-a1.mp3",
              message_id: 2,
              created_at: "2026-02-01T00:01:00Z",
              duration_seconds: 4.2,
            },
          ],
        },
        {
          user_id: "u2",
          agent_id: "a2",
          agent_name: "B",
          audios: [
            {
              audio_url: "https://example.com/opening-u2-a2.mp3",
              message_id: 3,
              created_at: "2026-02-01T00:02:00Z",
              duration_seconds: 4.0,
            },
          ],
        },
      ],
      voice_call_audios: [
        {
          user_id: "u1",
          agent_id: "a1",
          agent_name: "A",
          audios: [
            {
              audio_url: "https://example.com/call-u1-a1.mp3",
              message_id: 9,
              created_at: "2026-02-01T00:03:00Z",
              duration_seconds: 30.5,
            },
          ],
        },
      ],
    };

    const filtered = removeOpeningVoiceMessageAudios(voiceAudios);

    expect(filtered.voice_message_audios).toEqual([
      {
        user_id: "u1",
        agent_id: "a1",
        agent_name: "A",
        audios: [
          {
            audio_url: "https://example.com/reply-u1-a1.mp3",
            message_id: 2,
            created_at: "2026-02-01T00:01:00Z",
            duration_seconds: 4.2,
          },
        ],
      },
    ]);
    expect(filtered.voice_call_audios).toEqual(voiceAudios.voice_call_audios);
    expect(voiceAudios.voice_message_audios[0]?.audios).toHaveLength(2);
    expect(voiceAudios.voice_message_audios[1]?.audios).toHaveLength(1);
  });

  it("没有语音播报分组时返回空列表", () => {
    const filtered = removeOpeningVoiceMessageAudios({
      voice_message_audios: [],
      voice_call_audios: [],
    });

    expect(filtered.voice_message_audios).toEqual([]);
    expect(filtered.voice_call_audios).toEqual([]);
  });
});

describe("buildRollingDailyImageUsageSeries", () => {
  it("按日期输出每日近7天生图请求、成功滚动和与成功率", () => {
    const reports = Array.from({ length: 8 }, (_, index) => {
      const day = String(index + 1).padStart(2, "0");
      const value = index + 1;
      return buildReport({
        id: `r${value}`,
        report_date: `2026-02-${day}`,
        stats: buildStats({
          total_image_generation_requests: value * 3,
          total_image_generation_success: value * 2,
          image_generation_success_rate: 10 + value,
        }),
      });
    });

    const series = buildRollingDailyImageUsageSeries(reports);

    expect(series?.valuesByMetric.total_image_generation_requests).toEqual([
      3, 9, 18, 30, 45, 63, 84, 105,
    ]);
    expect(series?.valuesByMetric.total_image_generation_success).toEqual([
      2, 6, 12, 20, 30, 42, 56, 70,
    ]);
    const successRateValues =
      series?.valuesByMetric.image_generation_success_rate ?? [];
    expect(successRateValues).toHaveLength(8);
    successRateValues.forEach((value) => {
      expect(value).toBeCloseTo(66.6666667, 6);
    });
    expect(series?.dates[series.dates.length - 1]).toBe("2026-02-08");
  });

  it("支持自定义窗口并过滤周报", () => {
    const reports = [
      buildReport({
        id: "d1",
        report_date: "2026-02-01",
        stats: buildStats({
          total_image_generation_requests: 10,
          total_image_generation_success: 8,
          image_generation_success_rate: 10,
        }),
      }),
      buildReport({
        id: "d2",
        report_date: "2026-02-02",
        stats: buildStats({
          total_image_generation_requests: 20,
          total_image_generation_success: 15,
          image_generation_success_rate: 20,
        }),
      }),
      buildReport({
        id: "d3",
        report_date: "2026-02-03",
        stats: buildStats({
          total_image_generation_requests: 30,
          total_image_generation_success: 24,
          image_generation_success_rate: 30,
        }),
      }),
      buildReport({
        id: "w1",
        report_type: "weekly",
        report_date: "2026-W05",
        stats: buildStats({
          total_image_generation_requests: 999,
          total_image_generation_success: 999,
        }),
      }),
    ];

    const series = buildRollingDailyImageUsageSeries(reports, 2);

    expect(series?.dates).toEqual(["2026-02-01", "2026-02-02", "2026-02-03"]);
    expect(series?.valuesByMetric.total_image_generation_requests).toEqual([
      10, 30, 50,
    ]);
    expect(series?.valuesByMetric.total_image_generation_success).toEqual([
      8, 23, 39,
    ]);
    expect(
      series?.valuesByMetric.image_generation_success_rate[0] ?? 0,
    ).toBeCloseTo(80, 6);
    expect(
      series?.valuesByMetric.image_generation_success_rate[1] ?? 0,
    ).toBeCloseTo(76.6666667, 6);
    expect(
      series?.valuesByMetric.image_generation_success_rate[2] ?? 0,
    ).toBeCloseTo(78, 6);
  });

  it("没有日报数据时返回空值", () => {
    const series = buildRollingDailyImageUsageSeries([
      buildReport({ report_type: "weekly", report_date: "2026-W05" }),
    ]);
    expect(series).toBeNull();
  });
});

describe("buildDailyUsageTickText", () => {
  it("为日期补充周1-7标注", () => {
    const tickText = buildDailyUsageTickText(["2026-02-01", "2026-02-02"]);
    expect(tickText).toEqual(["2026-02-01\n周7", "2026-02-02\n周1"]);
  });

  it("非 ISO 日期保持原样", () => {
    const tickText = buildDailyUsageTickText(["2026-W05"]);
    expect(tickText).toEqual(["2026-W05"]);
  });

  it("非法日期保持原样", () => {
    const tickText = buildDailyUsageTickText(["2026-02-30"]);
    expect(tickText).toEqual(["2026-02-30"]);
  });
});

describe("sortReportsByDateDesc", () => {
  it("按日期倒序排序报告列表", () => {
    const reports = [
      buildReport({ id: "r1", report_date: "2026-02-01" }),
      buildReport({ id: "r2", report_date: "2026-02-03" }),
      buildReport({ id: "r3", report_date: "2026-01-31" }),
    ];

    const sorted = sortReportsByDateDesc(reports);

    expect(sorted.map((report) => report.id)).toEqual(["r2", "r1", "r3"]);
  });
});

describe("buildDailyTopAgentsTrendSeries", () => {
  it("按日期聚合日报 Top 角色并输出连线数据", () => {
    const reports = [
      buildReport({
        id: "r2",
        report_date: "2026-02-02",
        daily_top_agents_by_rounds: [
          {
            rank: 1,
            agent_name: "Role B",
            total_rounds: 30,
            user_count: 4,
            total_sessions: 5,
            active_sessions: 4,
          },
          {
            rank: 2,
            agent_name: "Role A",
            total_rounds: 18,
            user_count: 3,
            total_sessions: 4,
            active_sessions: 3,
          },
        ],
      }),
      buildReport({
        id: "r1",
        report_date: "2026-02-01",
        daily_top_agents_by_rounds: [
          {
            rank: 1,
            agent_name: "Role A",
            total_rounds: 24,
            user_count: 5,
            total_sessions: 6,
            active_sessions: 5,
          },
          {
            rank: 2,
            agent_name: "Role C",
            total_rounds: 12,
            user_count: 2,
            total_sessions: 3,
            active_sessions: 2,
          },
        ],
      }),
    ];

    const trend = buildDailyTopAgentsTrendSeries(reports);

    expect(trend?.dates).toEqual(["2026-02-01", "2026-02-02"]);
    expect(trend?.dailyTopAgentsByDate["2026-02-01"]?.length).toBe(2);
    expect(
      trend?.lines.find((line) => line.agent_name === "Role A")?.points,
    ).toEqual([
      {
        date: "2026-02-01",
        rank: 1,
        agent_name: "Role A",
        total_rounds: 24,
        user_count: 5,
      },
      {
        date: "2026-02-02",
        rank: 2,
        agent_name: "Role A",
        total_rounds: 18,
        user_count: 3,
      },
    ]);
  });

  it("支持限制每日 Top 数量", () => {
    const reports = [
      buildReport({
        id: "r1",
        report_date: "2026-02-01",
        daily_top_agents_by_rounds: [
          {
            rank: 1,
            agent_name: "Role A",
            total_rounds: 20,
            user_count: 3,
            total_sessions: 4,
            active_sessions: 3,
          },
          {
            rank: 2,
            agent_name: "Role B",
            total_rounds: 18,
            user_count: 2,
            total_sessions: 3,
            active_sessions: 2,
          },
        ],
      }),
    ];

    const trend = buildDailyTopAgentsTrendSeries(reports, 1);
    expect(trend?.dailyTopAgentsByDate["2026-02-01"]).toEqual([
      {
        date: "2026-02-01",
        rank: 1,
        agent_name: "Role A",
        total_rounds: 20,
        user_count: 3,
      },
    ]);
  });

  it("没有日报 Top 角色数据时返回空值", () => {
    const trend = buildDailyTopAgentsTrendSeries([
      buildReport({ report_type: "weekly", report_date: "2026-W05" }),
    ]);
    expect(trend).toBeNull();
    expect(DAILY_TOP_AGENTS_LIMIT).toBe(10);
  });
});
