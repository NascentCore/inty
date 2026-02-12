import { describe, expect, it } from "vitest";
import type { FestivalMemoryConfigItem } from "../types";
import {
  canShowFestivalMemoryResults,
  getFestivalMemoryRunStatusMeta,
  resolveFestivalMemoryRunStatus,
} from "../utils/festivalMemory";

const buildConfig = (
  overrides: Partial<FestivalMemoryConfigItem> = {},
): FestivalMemoryConfigItem => ({
  id: overrides.id ?? 1,
  festival_name: overrides.festival_name ?? "春节",
  festival_date: overrides.festival_date ?? "2026-02-10",
  prompt: overrides.prompt ?? "prompt",
  enabled: overrides.enabled ?? true,
  timezone: overrides.timezone ?? "UTC",
  run_at_date: overrides.run_at_date ?? "2026-02-12",
  run_at_hour: overrides.run_at_hour ?? 4,
  last_run_at: overrides.last_run_at ?? null,
  min_rounds_in_window: overrides.min_rounds_in_window ?? null,
  run_status: overrides.run_status,
  run_started_at: overrides.run_started_at,
  run_finished_at: overrides.run_finished_at,
  run_total_pairs: overrides.run_total_pairs,
  run_success_count: overrides.run_success_count,
  run_failed_count: overrides.run_failed_count,
  run_error_message: overrides.run_error_message,
});

describe("resolveFestivalMemoryRunStatus", () => {
  it("优先使用后端 run_status", () => {
    const config = buildConfig({ run_status: "running", last_run_at: null });
    expect(resolveFestivalMemoryRunStatus(config)).toBe("running");
  });

  it("未提供 run_status 且存在 last_run_at 时判定为 completed", () => {
    const config = buildConfig({
      run_status: undefined,
      last_run_at: "2026-02-12T09:01:00Z",
    });
    expect(resolveFestivalMemoryRunStatus(config)).toBe("completed");
  });

  it("未提供 run_status 且不存在 last_run_at 时判定为 idle", () => {
    const config = buildConfig({ run_status: undefined, last_run_at: null });
    expect(resolveFestivalMemoryRunStatus(config)).toBe("idle");
  });
});

describe("canShowFestivalMemoryResults", () => {
  it("运行中时不展示结果按钮", () => {
    const config = buildConfig({
      run_status: "running",
      run_finished_at: "2026-02-12T09:10:00Z",
    });
    expect(canShowFestivalMemoryResults(config)).toBe(false);
  });

  it("任务结束且有 run_finished_at 时展示结果按钮", () => {
    const config = buildConfig({
      run_status: "failed",
      run_finished_at: "2026-02-12T09:10:00Z",
      last_run_at: null,
    });
    expect(canShowFestivalMemoryResults(config)).toBe(true);
  });

  it("历史已执行（last_run_at）时展示结果按钮", () => {
    const config = buildConfig({
      run_status: undefined,
      run_finished_at: null,
      last_run_at: "2026-02-12T09:01:00Z",
    });
    expect(canShowFestivalMemoryResults(config)).toBe(true);
  });
});

describe("getFestivalMemoryRunStatusMeta", () => {
  it("返回可展示标签与颜色", () => {
    expect(getFestivalMemoryRunStatusMeta("running")).toEqual({
      label: "运行中",
      color: "processing",
    });
    expect(getFestivalMemoryRunStatusMeta("completed")).toEqual({
      label: "已完成",
      color: "success",
    });
    expect(getFestivalMemoryRunStatusMeta("failed")).toEqual({
      label: "失败",
      color: "error",
    });
    expect(getFestivalMemoryRunStatusMeta("idle")).toEqual({
      label: "未运行",
      color: "default",
    });
  });
});
