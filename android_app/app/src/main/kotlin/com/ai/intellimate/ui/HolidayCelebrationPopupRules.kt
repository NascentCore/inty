package com.ai.intellimate.ui

// CREATED_BY_AGENT

import java.util.Calendar
import java.util.Locale

/**
 * 节日庆祝弹窗显示规则（圣诞 + 新年）。
 *
 * 使用场景：
 * - App 打开/回到前台时，在主入口显示一次"非常吸睛"的节日庆祝弹窗。
 *
 * 设计决策：
 * - 此方法检查当前日期，只在2026年1月2日之前（含）返回 true。
 * - 实际的显示频率控制由 MainActivity 中的会话级标记（hasShownInSession）管理， 确保每个应用会话只显示一次，避免在应用恢复或登录状态变化时重复显示。
 * - 日期检查使用用户本地时区，确保符合用户所在地区的节日时间。
 * - 使用完整的年份、月份、日期比较，正确处理年份边界情况（避免1月时错误返回true）。
 *
 * 规则：
 * - 只在2026年1月2日之前（含）显示，2026年1月2日之后不再显示。
 * - 显示频率由调用方通过会话标记控制。
 */
internal object HolidayCelebrationPopupRules {

    /**
     * 检查当前是否应该显示节日庆祝弹窗。
     *
     * 设计决策：
     * - 使用用户本地时区检查日期，确保符合用户所在地区的节日时间
     * - 在2026年1月2日之后（不含）不再显示，避免节日过后仍显示庆祝弹窗
     * - 使用年份、月份和日期的完整比较，正确处理年份边界情况
     * - 月份从0开始（Calendar.DECEMBER = 11，Calendar.JANUARY = 0），日期从1开始
     *
     * @return true 如果当前日期在2026年1月2日之前（含），false 否则
     */
    fun shouldShowNow(): Boolean {
        val calendar = Calendar.getInstance(Locale.getDefault())
        val currentYear = calendar.get(Calendar.YEAR)
        val currentMonth = calendar.get(Calendar.MONTH)
        val currentDay = calendar.get(Calendar.DAY_OF_MONTH)

        // 设计决策：2026年1月2日之后不再显示
        // 使用完整的日期比较，避免年份边界问题
        // 如果年份大于2026，或者年份等于2026且月份大于1月，或者年份等于2026且月份等于1月且日期大于2，则不显示
        val cutoffYear = 2026
        val cutoffMonth = Calendar.JANUARY // 0
        val cutoffDay = 2

        val isAfterCutoff =
            when {
                currentYear > cutoffYear -> true
                currentYear < cutoffYear -> false
                // currentYear == cutoffYear
                currentMonth > cutoffMonth -> true
                currentMonth < cutoffMonth -> false
                // currentMonth == cutoffMonth
                currentDay > cutoffDay -> true
                else -> false // currentDay <= cutoffDay
            }

        return !isAfterCutoff
    }
}
