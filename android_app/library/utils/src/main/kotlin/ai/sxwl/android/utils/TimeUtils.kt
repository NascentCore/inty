package ai.sxwl.android.utils

import java.text.ParseException
import java.text.SimpleDateFormat
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.Date
import java.util.Locale
import java.util.concurrent.ConcurrentHashMap

/**
 * 时间工具类
 * 提供统一的时间处理API，整合了原DateUtils的功能
 *
 *主要功能：
 * - 时间整理
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
// ====================服务====================

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
// ==================== 时间整理 ====================

    /**
     * 时间表
     * @param timestamp 时间（毫秒）
     * @param pattern 格式模式
     * @return 删除后的时间字符串
     */
    fun format(timestamp: Long, pattern: String = DATE_TIME_PATTERN): String {
        return getFormatter(pattern).format(timestamp)
    }

    /**
     * 计时（秒）
     * @param timestamp 时间（秒）
     * @param pattern 格式模式
     * @return 删除后的时间字符串
     */
    fun formatFromSeconds(timestamp: Long?, pattern: String = DATE_TIME_PATTERN): String {
        if (timestamp == null || timestamp <= 0) return "Unknown"
        return format(timestamp * 1000, pattern)
    }

    /**
     * 解析时间字符串为时间
     * @param timeString 时间字符串
     * @param pattern 格式模式
     * @返回时间（毫秒）
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
        return try {
//检查风险溢出
            if (timestamp > Long.MAX_VALUE - ONE_DAY_MILLIS) {
                false
            } else {
                nowDateStr == format(timestamp + ONE_DAY_MILLIS, DATE_PATTERN)
            }
        } catch (e: Exception) {
            false
        }
    }

    /**
     * 判断是否是明天
     */
    fun isTomorrow(timestamp: Long): Boolean {
        return try {
//检查风险溢出
            if (timestamp < Long.MIN_VALUE + ONE_DAY_MILLIS) {
                false
            } else {
                nowDateStr == format(timestamp - ONE_DAY_MILLIS, DATE_PATTERN)
            }
        } catch (e: Exception) {
            false
        }
    }

    /**
     * 判断是否是前天
     */
    fun isBeforeYesterday(timestamp: Long): Boolean {
        return try {
//检查风险溢出
            if (timestamp > Long.MAX_VALUE - 2 * ONE_DAY_MILLIS) {
                false
            } else {
                nowDateStr == format(timestamp + 2 * ONE_DAY_MILLIS, DATE_PATTERN)
            }
        } catch (e: Exception) {
            false
        }
    }

    /**
     * 判断是否是后天
     */
    fun isAfterTomorrow(timestamp: Long): Boolean {
        return try {
//检查风险溢出
            if (timestamp < Long.MIN_VALUE + 2 * ONE_DAY_MILLIS) {
                false
            } else {
                nowDateStr == format(timestamp - 2 * ONE_DAY_MILLIS, DATE_PATTERN)
            }
        } catch (e: Exception) {
            false
        }
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
     * @param timestamp 时间（毫秒）
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
     * 获取相对时间描述（秒）
     * @param timestamp 时间（秒）
     * @return 相对时间字符串
     */
    fun getRelativeTimeFromSeconds(timestamp: Long?): String {
        if (timestamp == null || timestamp <= 0) return "Unknown"
        return getRelativeTime(timestamp * 1000)
    }
// ==================== 星期相关 ====================

    /**
     * 获取星期（中文）
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
// ====================便捷方法====================

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
     * 时间转Date对象
     */
    fun Long.toDate(): Date = Date(this)

    /**
     * Date对象转时间
     */
    fun Date.toMillis(): Long = this.time

    /**
     * 时间转日期字符串
     */
    fun Long.toDateStr(): String = format(this, DATE_PATTERN)

    /**
     * 时间转日期时间字符串
     */
    fun Long.toDateTimeStr(): String = format(this, DATE_TIME_PATTERN)
// ==================== 内部方法 ====================

    /**
     * 春节（支持自定义Locale）
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
//创建新的SimpleDateFormat实例，避免修改服务器的实例
                        val formatter = SimpleDateFormat(pattern, Locale.getDefault()).apply {
                            timeZone = java.util.TimeZone.getTimeZone("UTC")
                        }
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
// ==================== UTC 时间转换 ====================

    /**
     * 判断是否是今天（ZonedDateTime版本）
     */
    fun isToday(dateTime: ZonedDateTime): Boolean {
        val today = LocalDate.now(ZoneId.systemDefault())
        return dateTime.toLocalDate() == today
    }

    /**
     * 将UTC时间字符串转换为本地时间（智能显示）
     * @param utcString UTC时间字符串
     * @return 格式化后的本地时间字符串，今天显示HH:mm，其他显示MM/dd
     */
    fun convertUtcToLocal(utcString: String): String {
        if (utcString.isBlank()) return ""

        return runCatching {
            val instant = Instant.parse(utcString)
            val systemZone = ZoneId.systemDefault()
            val localDateTime = instant.atZone(systemZone)

            if (isToday(localDateTime)) {
                localDateTime.format(DateTimeFormatter.ofPattern("HH:mm"))
            } else {
                localDateTime.format(DateTimeFormatter.ofPattern("MM/dd"))
            }
        }.getOrNull() ?: ""
    }

    /**
     * 将UTC时间字符串转换为本地时间（完整格式）
     * @param utcString UTC时间字符串
     * @return 格式化后的本地时间字符串，格式为dd/MM/yyyy HH:mm
     */
    fun convertUtcToLocalFull(utcString: String): String {
        if (utcString.isBlank()) return ""

        return runCatching {
            val instant = Instant.parse(utcString)
            val systemZone = ZoneId.systemDefault()
            val localDateTime = instant.atZone(systemZone)
            localDateTime.format(DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm"))
        }.getOrNull() ?: ""
    }

    /**
     * 计时级计时器秒为年月日时分格式
     * 如果是年份，则不显示年份
     * @param timestampSeconds 秒级时间戳字符串
     * @return 格式化后的时间字符串，格式为：MM/dd或yyyy/MM/dd
     */
    fun formatTimestampToDateTime(timestampSeconds: String): String {
        return try {
            val seconds = timestampSeconds.toLong()
// 检查溢出风险：长。MAX_VALUE / 1000 避免故障
            if (seconds > Long.MAX_VALUE / 1000) {
                return timestampSeconds
            }
            val timestamp = seconds * 1000 // 转换为毫秒

            val systemZone = ZoneId.systemDefault()
            val instant = Instant.ofEpochMilli(timestamp)
            val localDateTime = instant.atZone(systemZone)

            val currentYear = LocalDate.now(systemZone).year
            val targetYear = localDateTime.year

            val pattern = if (targetYear == currentYear) {
                "MM/dd"
            } else {
                "yyyy/MM/dd"
            }

            localDateTime.format(DateTimeFormatter.ofPattern(pattern))
        } catch (e: NumberFormatException) {
// 数字格式错误，返回原始字符串
            timestampSeconds
        } catch (e: Exception) {
//其他异常，返回原始字符串
            timestampSeconds
        }
    }

    /**
     * 将ISO 8601格式的时间字符串转换为时钟脉冲
     * @param isoTimeString ISO 8601格式的时间字符串
     * @return每秒一个时间，如果解析失败返回null
     */
    fun parseIsoTimeToTimestamp(isoTimeString: String?): Long? {
        return try {
            isoTimeString ?: return null
            val instant = Instant.parse(isoTimeString)
            instant.toEpochMilli()
        } catch (e: Exception) {
            null
        }
    }

    /**
     * 将ISO 8601格式的时间字符串根据指定模式筛选为时间字符串
     * @param isoTimeString ISO 8601格式的时间字符串
     * @param pattern 时间格式pattern，默认为"yyyy-MM-dd"
     * @return 格式化后的时间字符串，如果解析失败返回null
     */
    fun formatIsoTimeToString(isoTimeString: String?, pattern: String = "yyyy-MM-dd"): String? {
        return try {
            isoTimeString ?: return null
            val instant = Instant.parse(isoTimeString)
            val systemZone = ZoneId.systemDefault()
            val localDateTime = instant.atZone(systemZone)
            localDateTime.format(DateTimeFormatter.ofPattern(pattern))
        } catch (e: Exception) {
            null
        }
    }

    /**
     * 将几十个转换为标准模式时间字符串
     * @param timestampMillis 毫秒计时器
     * @param pattern 时间格式pattern，默认为"yyyy-MM-dd"
     * @return 格式化后的时间字符串，如果解析失败返回null
     */
    fun formatTimestampToString(timestampMillis: Long?, pattern: String = "yyyy-MM-dd"): String? {
        return try {
            timestampMillis ?: return null
            if (timestampMillis <= 0) return null
            val instant = Instant.ofEpochMilli(timestampMillis)
            val systemZone = ZoneId.systemDefault()
            val localDateTime = instant.atZone(systemZone)
            localDateTime.format(DateTimeFormatter.ofPattern(pattern))
        } catch (e: Exception) {
            null
        }
    }
}
