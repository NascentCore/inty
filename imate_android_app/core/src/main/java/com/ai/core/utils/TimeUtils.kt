package com.ai.core.utils

import java.text.SimpleDateFormat
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.concurrent.ConcurrentHashMap

/**
 * 时间工具类 提供统一的时间处理API，整合了原DateUtils的功能
 *
 * 主要功能：
 * - 时间格式化
 * - 时间判断
 * - 时间计算
 * - 相对时间显示
 */
object TimeUtils {

    // ==================== 常量定义 ====================
    const val DATE_TIME_PATTERN = "yyyy-MM-dd HH:mm:ss"

    // ==================== 缓存机制 ====================
    private val formatterCache = ConcurrentHashMap<String, SimpleDateFormat>()

    private fun getFormatter(
        pattern: String,
        locale: Locale = Locale.getDefault(),
    ): SimpleDateFormat {
        val key = "${pattern}_${locale}"
        return formatterCache.getOrPut(key) { SimpleDateFormat(pattern, locale) }
    }

    /**
     * 格式化时间戳
     *
     * @param timestamp 时间戳（毫秒）
     * @param pattern 格式模式
     * @return 格式化后的时间字符串
     */
    fun format(timestamp: Long, pattern: String = DATE_TIME_PATTERN): String {
        return getFormatter(pattern).format(timestamp)
    }

    // ==================== UTC时间转换 ====================

    /** 判断是否是今天（ZonedDateTime版本） */
    fun isToday(dateTime: ZonedDateTime): Boolean {
        val today = LocalDate.now(ZoneId.systemDefault())
        return dateTime.toLocalDate() == today
    }

    /**
     * 将UTC时间字符串转换为本地时间（智能显示）
     *
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
            }
            .getOrNull() ?: ""
    }

    /**
     * 将UTC时间字符串转换为本地时间（完整格式）
     *
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
            }
            .getOrNull() ?: ""
    }

    /**
     * 将UTC时间字符串转换为本地时间（UI 展示用，美国常用格式）
     *
     * @param utcString UTC时间字符串（ISO 8601）
     * @return 格式化后的本地时间字符串，格式为 MM/dd/yyyy h:mm a（如 02/06/2026 3:04 PM）
     */
    fun convertUtcToLocalFullForDisplay(utcString: String): String {
        if (utcString.isBlank()) return ""

        return runCatching {
                val instant = Instant.parse(utcString)
                val systemZone = ZoneId.systemDefault()
                val localDateTime = instant.atZone(systemZone)
                localDateTime.format(DateTimeFormatter.ofPattern("MM/dd/yyyy h:mm a", Locale.US))
            }
            .getOrNull() ?: ""
    }

    /**
     * 将ISO 8601格式的时间字符串转换为毫秒时间戳
     *
     * @param isoTimeString ISO 8601格式的时间字符串
     * @return 毫秒时间戳，如果解析失败返回null
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
     * 将毫秒时间戳转换为标准pattern时间字符串
     *
     * @param timestampMillis 毫秒时间戳
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
