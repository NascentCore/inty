/**
 * CREATED_BY_AGENT
 */
import { describe, it, expect } from "vitest";
import {
  buildDailyUsageSeries,
  sortReportsByDateDesc,
} from "../utils/userAnalyticsReports";
import type {
  UserAnalyticsReportItem,
  UserAnalyticsStatsResponse,
} from "../types";

const buildStats = (
  overrides: Partial<UserAnalyticsStatsResponse> = {},
): UserAnalyticsStatsResponse => ({
  total_new_users: 0,
  total_chat_initiators: 0,
  total_user_messages: 0,
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
          total_user_messages: 20,
          total_image_generation_requests: 4,
          total_live_chat_sessions: 2,
          total_voice_requests: 1,
        }),
      }),
      buildReport({
        id: "r1",
        report_date: "2026-02-01",
        stats: buildStats({
          total_user_messages: 10,
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
    expect(series?.valuesByMetric.total_image_generation_requests).toEqual([
      2, 4,
    ]);
    expect(series?.valuesByMetric.total_live_chat_sessions).toEqual([1, 2]);
    expect(series?.valuesByMetric.total_voice_requests).toEqual([0, 1]);
  });

  it("没有日报数据时返回空值", () => {
    const series = buildDailyUsageSeries([
      buildReport({ report_type: "weekly", report_date: "2026-W05" }),
    ]);
    expect(series).toBeNull();
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
