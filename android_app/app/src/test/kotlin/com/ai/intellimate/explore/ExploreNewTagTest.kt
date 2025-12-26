/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.explore

import java.time.ZoneId
import java.time.ZonedDateTime
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ExploreNewTagTest {

    @Test
    fun showNewTag_whenCreatedWithinLast7Days_inLocalTimeZone() {
        val zone = ZoneId.of("Asia/Shanghai")
        val now = ZonedDateTime.of(2025, 12, 26, 12, 0, 0, 0, zone)

        val createdAt = now.minusDays(6).minusHours(23).toInstant().toString()
        assertTrue(shouldShowNewTag(createdAtUtcIso = createdAt, now = now))
    }

    @Test
    fun showNewTag_whenCreatedExactly7DaysAgo_inLocalTimeZone() {
        val zone = ZoneId.of("Asia/Shanghai")
        val now = ZonedDateTime.of(2025, 12, 26, 12, 0, 0, 0, zone)

        val createdAt = now.minusDays(7).toInstant().toString()
        assertTrue(shouldShowNewTag(createdAtUtcIso = createdAt, now = now))
    }

    @Test
    fun hideNewTag_whenCreatedEarlierThan7DaysAgo_inLocalTimeZone() {
        val zone = ZoneId.of("Asia/Shanghai")
        val now = ZonedDateTime.of(2025, 12, 26, 12, 0, 0, 0, zone)

        val createdAt = now.minusDays(7).minusNanos(1).toInstant().toString()
        assertFalse(shouldShowNewTag(createdAtUtcIso = createdAt, now = now))
    }

    @Test
    fun hideNewTag_whenCreatedAtIsInvalid() {
        val zone = ZoneId.of("Asia/Shanghai")
        val now = ZonedDateTime.of(2025, 12, 26, 12, 0, 0, 0, zone)

        assertFalse(shouldShowNewTag(createdAtUtcIso = "not-a-timestamp", now = now))
    }
}

