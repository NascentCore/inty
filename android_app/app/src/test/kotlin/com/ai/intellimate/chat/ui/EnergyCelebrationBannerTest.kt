/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.chat.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class EnergyCelebrationBannerTest {

    @Test
    fun resolveCelebrationLevel_firstPoint_returnsFirst() {
        assertEquals(EnergyCelebrationLevel.First, resolveCelebrationLevel(1))
    }

    @Test
    fun resolveCelebrationLevel_tensPoints_returnsTens() {
        assertEquals(EnergyCelebrationLevel.Tens, resolveCelebrationLevel(10))
        assertEquals(EnergyCelebrationLevel.Tens, resolveCelebrationLevel(20))
        assertEquals(EnergyCelebrationLevel.Tens, resolveCelebrationLevel(30))
        assertEquals(EnergyCelebrationLevel.Tens, resolveCelebrationLevel(40))
        assertEquals(EnergyCelebrationLevel.Tens, resolveCelebrationLevel(50))
        assertEquals(EnergyCelebrationLevel.Tens, resolveCelebrationLevel(60))
        assertEquals(EnergyCelebrationLevel.Tens, resolveCelebrationLevel(70))
        assertEquals(EnergyCelebrationLevel.Tens, resolveCelebrationLevel(80))
        assertEquals(EnergyCelebrationLevel.Tens, resolveCelebrationLevel(90))
    }

    @Test
    fun resolveCelebrationLevel_hundredsPoints_returnsHundreds() {
        assertEquals(EnergyCelebrationLevel.Hundreds, resolveCelebrationLevel(100))
        assertEquals(EnergyCelebrationLevel.Hundreds, resolveCelebrationLevel(200))
        assertEquals(EnergyCelebrationLevel.Hundreds, resolveCelebrationLevel(300))
        assertEquals(EnergyCelebrationLevel.Hundreds, resolveCelebrationLevel(400))
        assertEquals(EnergyCelebrationLevel.Hundreds, resolveCelebrationLevel(500))
        assertEquals(EnergyCelebrationLevel.Hundreds, resolveCelebrationLevel(600))
        assertEquals(EnergyCelebrationLevel.Hundreds, resolveCelebrationLevel(700))
        assertEquals(EnergyCelebrationLevel.Hundreds, resolveCelebrationLevel(800))
        assertEquals(EnergyCelebrationLevel.Hundreds, resolveCelebrationLevel(900))
    }

    @Test
    fun resolveCelebrationLevel_thousandsPoints_returnsThousands() {
        assertEquals(EnergyCelebrationLevel.Thousands, resolveCelebrationLevel(1000))
        assertEquals(EnergyCelebrationLevel.Thousands, resolveCelebrationLevel(2000))
        assertEquals(EnergyCelebrationLevel.Thousands, resolveCelebrationLevel(5000))
        assertEquals(EnergyCelebrationLevel.Thousands, resolveCelebrationLevel(10000))
        assertEquals(EnergyCelebrationLevel.Thousands, resolveCelebrationLevel(100000))
    }

    @Test
    fun resolveCelebrationLevel_nonMilestonePoints_returnsNull() {
        assertNull(resolveCelebrationLevel(0))
        assertNull(resolveCelebrationLevel(2))
        assertNull(resolveCelebrationLevel(5))
        assertNull(resolveCelebrationLevel(9))
        assertNull(resolveCelebrationLevel(11))
        assertNull(resolveCelebrationLevel(25))
        assertNull(resolveCelebrationLevel(99))
        assertNull(resolveCelebrationLevel(101))
        assertNull(resolveCelebrationLevel(150))
        assertNull(resolveCelebrationLevel(999))
        assertNull(resolveCelebrationLevel(1001)) // 不是 1000 的倍数
        assertNull(resolveCelebrationLevel(1500)) // 不是 1000 的倍数
    }

    @Test
    fun resolveCelebrationLevel_negativePoints_returnsNull() {
        assertNull(resolveCelebrationLevel(-1))
        assertNull(resolveCelebrationLevel(-10))
        assertNull(resolveCelebrationLevel(-100))
    }
}
