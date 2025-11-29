package com.ai.intellimate.settings.check

import java.util.Calendar

/**
 * 获取当前月份的总天数和今天的日期。
 * @return Pair<总天数, 今天是第几天>
 */
fun getCurrentMonthInfo(): Pair<Int, Int> {
    val calendar = Calendar.getInstance()
    // 获取当月最大天数
    val daysInMonth = calendar.getActualMaximum(Calendar.DAY_OF_MONTH)
    // 获取今天是第几天（1-based）
    val today = calendar.get(Calendar.DAY_OF_MONTH)
    return Pair(daysInMonth, today)
}