/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.explore

import java.time.Instant
import java.time.ZoneId
import java.time.ZonedDateTime

private const val NEW_TAG_WINDOW_DAYS = 7L

/**
 * Explore 角色卡片 “NEW” 标签显示规则：
 * - 角色创建时间（UTC ISO8601 字符串）转换到设备本地时区后
 * - 若在本地时间过去 [NEW_TAG_WINDOW_DAYS] 天内（含边界），则显示 NEW 标签
 */
internal fun shouldShowNewTag(
    createdAtUtcIso: String,
    now: ZonedDateTime = ZonedDateTime.now(ZoneId.systemDefault()),
): Boolean {
    if (createdAtUtcIso.isBlank()) return false

    val createdInstant = runCatching { Instant.parse(createdAtUtcIso) }.getOrNull() ?: return false
    val createdLocal = createdInstant.atZone(now.zone)
    val threshold = now.minusDays(NEW_TAG_WINDOW_DAYS)
    return !createdLocal.isBefore(threshold)
}

