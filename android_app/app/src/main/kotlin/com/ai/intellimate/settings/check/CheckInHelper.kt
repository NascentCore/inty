package com.ai.intellimate.settings.check

import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Calendar
import java.util.Locale

/**
 * 获取当前月份的总天数和今天的日期。
 * @return Pair<总天数, 今天是第几天>
 */
fun getCurrentMonthInfo(): Pair<Int, Int> {
    val calendar = Calendar.getInstance()
    // 获取当月最大天数
    val daysInMonth = calendar.getActualMaximum(Calendar.DAY_OF_MONTH)
    // 获取今天是第几天（1-based）
//    val today = calendar.get(Calendar.DAY_OF_MONTH)
    val today = 14  // 测试代码
    return Pair(daysInMonth, today)
}

fun getCurrentMonthAbbreviation(): String {
    // 1. 获取当前日期
    val currentDate = LocalDate.now()

    // 2. 定义日期时间格式化器
    // "MMM" 是月份的缩写格式（例如 Jan, Feb, Mar, Nov 等）。
    // 还需要指定语言环境（Locale），确保输出的是英文缩写（例如 "Nov" 而不是中文的 "11月"）。
    val formatter = DateTimeFormatter.ofPattern("MMM", Locale.ENGLISH)

    // 3. 格式化日期并获取月份缩写
    val monthAbbreviation = currentDate.format(formatter)

    return monthAbbreviation
}