// CREATED_BY_AGENT
// UTC 时间格式化工具函数

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

dayjs.extend(utc);

/**
 * 格式化时间为 UTC 时间字符串，带 UTC 标注
 * @param time 时间字符串、Date 对象或时间戳
 * @param format 格式字符串，默认 "YYYY-MM-DD HH:mm:ss"
 * @returns 格式化后的 UTC 时间字符串，带 "(UTC)" 标注
 */
export function formatUtcTime(
  time: string | Date | number | null | undefined,
  format: string = "YYYY-MM-DD HH:mm:ss",
): string {
  if (!time) return "-";
  return `${dayjs.utc(time).format(format)} (UTC)`;
}

/**
 * 格式化时间为 UTC 时间字符串，不带标注
 * @param time 时间字符串、Date 对象或时间戳
 * @param format 格式字符串，默认 "YYYY-MM-DD HH:mm:ss"
 * @returns 格式化后的 UTC 时间字符串
 */
export function formatUtcTimeRaw(
  time: string | Date | number | null | undefined,
  format: string = "YYYY-MM-DD HH:mm:ss",
): string {
  if (!time) return "-";
  return dayjs.utc(time).format(format);
}

/**
 * 格式化时间为 UTC 时间字符串，仅显示时间部分
 * @param time 时间字符串、Date 对象或时间戳
 * @returns 格式化后的 UTC 时间字符串 (HH:mm:ss)
 */
export function formatUtcTimeOnly(
  time: string | Date | number | null | undefined,
): string {
  if (!time) return "-";
  return dayjs.utc(time).format("HH:mm:ss");
}

/**
 * 获取当前 UTC 时间的格式化字符串
 * @param format 格式字符串
 * @returns 格式化后的当前 UTC 时间字符串
 */
export function getCurrentUtcTime(
  format: string = "YYYY-MM-DD_HH-mm-ss",
): string {
  return dayjs.utc().format(format);
}
