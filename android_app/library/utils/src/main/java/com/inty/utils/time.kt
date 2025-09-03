package com.inty.utils

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter


fun isToday(dateTime: ZonedDateTime): Boolean {
    val today = LocalDate.now(ZoneId.systemDefault())
    return dateTime.toLocalDate() == today
}

fun convertUtcToLocal(utcString: String): String {
    val instant = Instant.parse(utcString)

    val localDateTime = instant.atZone(ZoneId.systemDefault())


    return if (isToday(localDateTime)) {
        localDateTime.format(DateTimeFormatter.ofPattern("HH:mm"))
    } else {
        localDateTime.format(DateTimeFormatter.ofPattern("MM/dd"))
    }
}

fun convertUtcToLocalFull(utcString: String): String {
    val instant = Instant.parse(utcString)

    val localDateTime = instant.atZone(ZoneId.systemDefault())


    return localDateTime.format(DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm"))
}

/**
 * 格式化秒级时间戳为年月日时分格式
 * 如果是今年，则不显示年份
 * @param timestampSeconds 秒级时间戳字符串
 * @return 格式化后的时间字符串，格式为：MM-dd或 yyyy-MM-dd
 */
fun formatTimestampToDateTime(timestampSeconds: String): String {
    return try {
        val timestamp = timestampSeconds.toLong() * 1000 // 转换为毫秒
        val instant = Instant.ofEpochMilli(timestamp)
        val localDateTime = instant.atZone(ZoneId.systemDefault())

        val currentYear = LocalDate.now(ZoneId.systemDefault()).year
        val targetYear = localDateTime.year

        val pattern = if (targetYear == currentYear) {
            "MM/dd"
        } else {
            "yyyy/MM/dd"
        }

        localDateTime.format(DateTimeFormatter.ofPattern(pattern))
    } catch (e: Exception) {
        // 如果解析失败，返回原始字符串
        timestampSeconds
    }
}

/**
 * 将ISO 8601格式的时间字符串转换为毫秒时间戳
 * @param isoTimeString ISO 8601格式的时间字符串，如："2025-09-01T06:03:15.383000Z"
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
 * 将ISO 8601格式的时间字符串根据指定pattern格式化为时间字符串
 * @param isoTimeString ISO 8601格式的时间字符串，如："2025-09-01T06:03:15.383000Z"
 * @param pattern 时间格式pattern，默认为"yyyy-MM-dd"
 * @return 格式化后的时间字符串，如果解析失败返回null
 */
fun formatIsoTimeToString(isoTimeString: String?, pattern: String = "yyyy-MM-dd"): String? {
    return try {
        isoTimeString ?: return null
        val instant = Instant.parse(isoTimeString)
        val localDateTime = instant.atZone(ZoneId.systemDefault())
        localDateTime.format(DateTimeFormatter.ofPattern(pattern))
    } catch (e: Exception) {
        null
    }
}

/**
 * 将毫秒时间戳转换为标准pattern时间字符串
 * @param timestampMillis 毫秒时间戳
 * @param pattern 时间格式pattern，默认为"yyyy-MM-dd"
 * @return 格式化后的时间字符串，如果解析失败返回null
 */
fun formatTimestampToString(timestampMillis: Long?, pattern: String = "yyyy-MM-dd"): String? {
    return try {
        timestampMillis ?: return null
        if (timestampMillis <= 0) return null
        val instant = Instant.ofEpochMilli(timestampMillis)
        val localDateTime = instant.atZone(ZoneId.systemDefault())
        localDateTime.format(DateTimeFormatter.ofPattern(pattern))
    } catch (e: Exception) {
        null
    }
}
