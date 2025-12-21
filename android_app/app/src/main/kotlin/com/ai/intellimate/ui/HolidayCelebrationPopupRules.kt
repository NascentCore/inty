package com.ai.intellimate.ui

// CREATED_BY_AGENT

import ai.sxwl.android.data.store.IntySetting
import java.util.Calendar
import java.util.Locale

/**
 * 节日庆祝弹窗显示规则（圣诞 + 新年）。
 *
 * 使用场景：
 * - App 打开/回到前台时，在主入口显示一次“非常吸睛”的节日庆祝弹窗。
 *
 * 规则：
 * - 只在每年 12/01～12/25（含 12/25）内可显示。
 * - 12/25 之后（从 12/26 起）永不再显示。
 * - “记录日期”：同一天最多弹一次（记录 yyyyMMdd）。
 */
internal object HolidayCelebrationPopupRules {

    private const val MONTH_DECEMBER = 11 // Calendar.MONTH：从 0 开始，12 月为 11
    private const val DAY_CUTOFF = 25

    fun shouldShowNow(calendar: Calendar = Calendar.getInstance()): Boolean {
        if (!isWithinPopupWindow(calendar)) return false

        val today = yyyymmdd(calendar)
        val lastShown = IntySetting.getHolidayCelebrationLastShownYmd()
        return lastShown != today
    }

    fun markShownToday(calendar: Calendar = Calendar.getInstance()) {
        IntySetting.setHolidayCelebrationLastShownYmd(yyyymmdd(calendar))
    }

    private fun isWithinPopupWindow(calendar: Calendar): Boolean {
        val month = calendar.get(Calendar.MONTH)
        if (month != MONTH_DECEMBER) return false

        val day = calendar.get(Calendar.DAY_OF_MONTH)
        if (day <= 0) return false
        return day <= DAY_CUTOFF
    }

    private fun yyyymmdd(calendar: Calendar): String {
        val year = calendar.get(Calendar.YEAR)
        val month1Based = calendar.get(Calendar.MONTH) + 1
        val day = calendar.get(Calendar.DAY_OF_MONTH)
        return String.format(Locale.US, "%04d%02d%02d", year, month1Based, day)
    }
}

