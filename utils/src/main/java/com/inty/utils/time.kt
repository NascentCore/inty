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
