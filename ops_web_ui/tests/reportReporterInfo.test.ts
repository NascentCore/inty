import { describe, expect, it } from "vitest";

import { buildReporterInfoRows } from "../utils/reportReporterInfo";

describe("reportReporterInfo utils", () => {
  it("returns fallback rows when reporter info is missing", () => {
    const rows = buildReporterInfoRows(null);
    expect(rows).toEqual([
      { label: "昵称", value: "无" },
      { label: "邮箱", value: "无" },
      { label: "手机号", value: "无" },
      { label: "Readable ID", value: "无" },
      { label: "注册时间 (UTC)", value: "无" },
    ]);
  });

  it("falls back to user id when readable_id is missing", () => {
    const rows = buildReporterInfoRows({
      id: "user-01KTEST",
      readable_id: null,
      nickname: "Guest",
      email: null,
      phone: null,
      created_at: null,
    });

    expect(rows.find((row) => row.label === "Readable ID")?.value).toBe(
      "user-01KTEST",
    );
  });

  it("formats reporter info rows with normalized values", () => {
    const rows = buildReporterInfoRows({
      id: "user-01KTEST",
      readable_id: "RPT12345",
      nickname: "  ReportTester  ",
      email: "tester@example.com",
      phone: "  ",
      created_at: "2026-02-24T18:57:54Z",
    });

    expect(rows).toEqual([
      { label: "昵称", value: "ReportTester" },
      { label: "邮箱", value: "tester@example.com" },
      { label: "手机号", value: "无" },
      { label: "Readable ID", value: "RPT12345" },
      { label: "注册时间 (UTC)", value: "2026-02-24 18:57:54" },
    ]);
  });
});
