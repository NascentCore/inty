package ai.sxwl.android.utils

import java.text.ParseException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.ConcurrentHashMap

/**
 * 时间工具类
 * 提供统一的时间处理API，整合了原DateUtils的功能
 *
 * 主要功能：
 * - 时间格式化
 * - 时间判断
 * - 时间计算
 * - 相对时间显示
 */
object TimeUtils {

    // ==================== 常量定义 ====================

    const val FULL_PATTERN = "yyyy-MM-dd EE HH:mm:ss"
    const val FULL_CN_PATTERN = "yyyy-MM-dd EEEE HH:mm:ss"
    const val DATE_WEEK_TIME_PATTERN = "yyyy-MM-dd EEEE HH:mm"
    const val MILLIS_PATTERN = "yyyy-MM-dd HH:mm:ss.SSSZZZ"
    const val DATE_TIME_PATTERN = "yyyy-MM-dd HH:mm:ss"
    const val TIME_PATTERN = "HH:mm:ss"
    const val DATE_PATTERN = "yyyy-MM-dd"
    const val WEEK_PATTERN = "EE"
    const val ONE_DAY_MILLIS = 24 * 60 * 60 * 1000L

    // ==================== 缓存机制 ====================

    private val formatterCache = ConcurrentHashMap<String, SimpleDateFormat>()

    private fun getFormatter(
        pattern: String,
        locale: Locale = Locale.getDefault()
    ): SimpleDateFormat {
        val key = "${pattern}_${locale}"
        return formatterCache.getOrPut(key) {
            SimpleDateFormat(pattern, locale)
        }
    }

    // ==================== 当前时间相关 ====================

    /**
     * 当前时间毫秒值
     */
    val nowMillis: Long get() = System.currentTimeMillis()

    /**
     * 当前时间字符串 (yyyy-MM-dd HH:mm:ss)
     */
    val nowDateTimeStr: String get() = format(nowMillis, DATE_TIME_PATTERN)

    /**
     * 当前日期字符串 (yyyy-MM-dd)
     */
    val nowDateStr: String get() = format(nowMillis, DATE_PATTERN)

    /**
     * 当前时间字符串 (HH:mm:ss)
     */
    val nowTimeStr: String get() = format(nowMillis, TIME_PATTERN)

    /**
     * 当前星期
     */
    val nowWeek: String get() = format(nowMillis, WEEK_PATTERN)

    // ==================== 时间格式化 ====================

    /**
     * 格式化时间戳
     * @param timestamp 时间戳（毫秒）
     * @param pattern 格式模式
     * @return 格式化后的时间字符串
     */
    fun format(timestamp: Long, pattern: String = DATE_TIME_PATTERN): String {
        return getFormatter(pattern).format(timestamp)
    }

    /**
     * 格式化时间戳（秒）
     * @param timestamp 时间戳（秒）
     * @param pattern 格式模式
     * @return 格式化后的时间字符串
     */
    fun formatFromSeconds(timestamp: Long?, pattern: String = DATE_TIME_PATTERN): String {
        if (timestamp == null || timestamp <= 0) return "Unknown"
        return format(timestamp * 1000, pattern)
    }

    /**
     * 解析时间字符串为时间戳
     * @param timeString 时间字符串
     * @param pattern 格式模式
     * @return 时间戳（毫秒）
     */
    @Throws(ParseException::class)
    fun parse(timeString: String, pattern: String = DATE_TIME_PATTERN): Long {
        return getFormatter(pattern).parse(timeString)?.time ?: 0L
    }

    // ==================== 时间判断 ====================

    /**
     * 判断是否是今天
     */
    fun isToday(timestamp: Long): Boolean {
        return nowDateStr == format(timestamp, DATE_PATTERN)
    }

    /**
     * 判断是否是昨天
     */
    fun isYesterday(timestamp: Long): Boolean {
        return nowDateStr == format(timestamp + ONE_DAY_MILLIS, DATE_PATTERN)
    }

    /**
     * 判断是否是明天
     */
    fun isTomorrow(timestamp: Long): Boolean {
        return nowDateStr == format(timestamp - ONE_DAY_MILLIS, DATE_PATTERN)
    }

    /**
     * 判断是否是前天
     */
    fun isBeforeYesterday(timestamp: Long): Boolean {
        return nowDateStr == format(timestamp + 2 * ONE_DAY_MILLIS, DATE_PATTERN)
    }

    /**
     * 判断是否是后天
     */
    fun isAfterTomorrow(timestamp: Long): Boolean {
        return nowDateStr == format(timestamp - 2 * ONE_DAY_MILLIS, DATE_PATTERN)
    }

    // ==================== 时间计算 ====================

    /**
     * 计算两个时间的天数差
     * @param start 开始时间（毫秒）
     * @param end 结束时间（毫秒）
     * @return 天数差
     */
    fun daysBetween(start: Long, end: Long = nowMillis): Int {
        return ((end - start) / ONE_DAY_MILLIS).toInt()
    }

    /**
     * 计算两个时间字符串的天数差
     * @param start 开始时间字符串
     * @param end 结束时间字符串
     * @param pattern 时间格式
     * @return 天数差
     */
    @Throws(ParseException::class)
    fun daysBetween(start: String, end: String = nowDateStr, pattern: String = DATE_PATTERN): Int {
        val startMillis = parse(start, pattern)
        val endMillis = parse(end, pattern)
        return daysBetween(startMillis, endMillis)
    }

    // ==================== 相对时间显示 ====================

    /**
     * 获取相对时间描述
     * @param timestamp 时间戳（毫秒）
     * @return 相对时间字符串，如：刚刚、2小时前、3天前等
     */
    fun getRelativeTime(timestamp: Long): String {
        val now = System.currentTimeMillis()
        val diff = (now - timestamp) / 1000

        return when {
            diff < 60 -> "刚刚"
            diff < 3600 -> "${diff / 60}分钟前"
            diff < 86400 -> "${diff / 3600}小时前"
            diff < 2592000 -> "${diff / 86400}天前"
            diff < 31536000 -> "${diff / 2592000}个月前"
            else -> "${diff / 31536000}年前"
        }
    }

    /**
     * 获取相对时间描述（秒时间戳）
     * @param timestamp 时间戳（秒）
     * @return 相对时间字符串
     */
    fun getRelativeTimeFromSeconds(timestamp: Long?): String {
        if (timestamp == null || timestamp <= 0) return "Unknown"
        return getRelativeTime(timestamp * 1000)
    }

    // ==================== 星期相关 ====================

    /**
     * 获取星期（英文）
     */
    fun getWeekEn(timestamp: Long): String {
        return format(timestamp, WEEK_PATTERN, Locale.US)
    }

    /**
     * 获取星期（中文）
     */
    fun getWeekCn(timestamp: Long): String {
        return format(timestamp, WEEK_PATTERN, Locale.CHINA)
    }

    /**
     * 获取星期（当前语言）
     */
    fun getWeek(timestamp: Long): String {
        return format(timestamp, WEEK_PATTERN)
    }

    // ==================== 便捷方法 ====================

    /**
     * 获取昨天日期字符串
     */
    val yesterdayDate: String get() = format(nowMillis - ONE_DAY_MILLIS, DATE_PATTERN)

    /**
     * 获取明天日期字符串
     */
    val tomorrowDate: String get() = format(nowMillis + ONE_DAY_MILLIS, DATE_PATTERN)

    /**
     * 获取后天日期字符串
     */
    val afterTomorrowDate: String get() = format(nowMillis + 2 * ONE_DAY_MILLIS, DATE_PATTERN)

    /**
     * 获取前天日期字符串
     */
    val beforeYesterdayDate: String get() = format(nowMillis - 2 * ONE_DAY_MILLIS, DATE_PATTERN)

    // ==================== 扩展方法 ====================

    /**
     * 时间戳转Date对象
     */
    fun Long.toDate(): Date = Date(this)

    /**
     * Date对象转时间戳
     */
    fun Date.toMillis(): Long = this.time

    /**
     * 时间戳转日期字符串
     */
    fun Long.toDateStr(): String = format(this, DATE_PATTERN)

    /**
     * 时间戳转日期时间字符串
     */
    fun Long.toDateTimeStr(): String = format(this, DATE_TIME_PATTERN)

    // ==================== 内部方法 ====================

    /**
     * 格式化时间戳（支持自定义Locale）
     */
    private fun format(timestamp: Long, pattern: String, locale: Locale): String {
        return getFormatter(pattern, locale).format(timestamp)
    }

    /**
     * 解析ISO时间字符串
     */
    fun parseIsoTime(isoTimeString: String?): Long? {
        if (isoTimeString.isNullOrEmpty()) return null

        return try {
            // 尝试解析ISO 8601格式
            val instant = java.time.Instant.parse(isoTimeString)
            instant.toEpochMilli()
        } catch (e: Exception) {
            try {
                // 尝试其他常见格式
                val patterns = listOf(
                    "yyyy-MM-dd'T'HH:mm:ss'Z'",
                    "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'",
                    "yyyy-MM-dd'T'HH:mm:ss",
                    "yyyy-MM-dd HH:mm:ss",
                    "yyyy-MM-dd"
                )

                for (pattern in patterns) {
                    try {
                        val formatter = getFormatter(pattern)
                        formatter.timeZone = java.util.TimeZone.getTimeZone("UTC")
                        return formatter.parse(isoTimeString)?.time
                    } catch (e: ParseException) {
                        // 继续尝试下一个格式
                    }
                }
                null
            } catch (e: Exception) {
                null
            }
        }
    }
}
