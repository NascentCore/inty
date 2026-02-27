/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.chat.utils

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class VipChatCreditPolicyTest {

    @Test
    fun `hasVipTag - ignores nulls and is case insensitive`() {
        val tags = listOf(null, "Featured", "VIP", "other")
        assertTrue(VipChatCreditPolicy.hasVipTag(tags))
    }

    @Test
    fun `hasVipTag - false for null or empty`() {
        assertFalse(VipChatCreditPolicy.hasVipTag(null))
        assertFalse(VipChatCreditPolicy.hasVipTag(emptyList()))
    }

    @Test
    fun `shouldDeductCredits - subscribed user is exempt`() {
        val tags = listOf("vip")
        assertFalse(VipChatCreditPolicy.shouldDeductCredits(isSubscribed = true, tags = tags))
    }

    @Test
    fun `shouldDeductCredits - non subscribed vip agent requires deduction`() {
        val tags = listOf("vip")
        assertTrue(VipChatCreditPolicy.shouldDeductCredits(isSubscribed = false, tags = tags))
    }
}
