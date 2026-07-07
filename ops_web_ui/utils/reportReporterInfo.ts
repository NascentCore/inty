import type { ReporterUserInfo } from "../types";
import { formatUtcTimeRaw } from "./dateUtils";
import { userDisplayId } from "./userDisplayId";

export interface ReporterInfoRow {
  label: string;
  value: string;
}

function getDisplayValue(value: string | null | undefined): string {
  if (!value) {
    return "无";
  }
  const trimmedValue = value.trim();
  return trimmedValue.length > 0 ? trimmedValue : "无";
}

export function buildReporterInfoRows(
  reporterUserInfo: ReporterUserInfo | null | undefined,
): ReporterInfoRow[] {
  if (!reporterUserInfo) {
    return [
      { label: "昵称", value: "无" },
      { label: "邮箱", value: "无" },
      { label: "手机号", value: "无" },
      { label: "Readable ID", value: "无" },
      { label: "注册时间 (UTC)", value: "无" },
    ];
  }

  return [
    { label: "昵称", value: getDisplayValue(reporterUserInfo.nickname) },
    { label: "邮箱", value: getDisplayValue(reporterUserInfo.email) },
    { label: "手机号", value: getDisplayValue(reporterUserInfo.phone) },
    {
      label: "Readable ID",
      value: getDisplayValue(userDisplayId(reporterUserInfo)),
    },
    {
      label: "注册时间 (UTC)",
      value: reporterUserInfo.created_at
        ? formatUtcTimeRaw(reporterUserInfo.created_at)
        : "无",
    },
  ];
}
