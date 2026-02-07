/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.chat.utils

/** VIP 聊天积分扣除规则统一入口，避免分散在 ViewModel 内。 */
object VipChatCreditPolicy {
    fun hasVipTag(tags: List<String?>?): Boolean {
        return tags?.any { it?.contains("vip", ignoreCase = true) == true } == true
    }

    fun shouldDeductCredits(isSubscribed: Boolean, tags: List<String?>?): Boolean {
        return !isSubscribed && hasVipTag(tags)
    }
}
