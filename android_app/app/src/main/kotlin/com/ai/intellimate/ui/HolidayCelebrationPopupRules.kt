package com.ai.intellimate.ui

// CREATED_BY_AGENT

/**
 * 节日庆祝弹窗显示规则（圣诞 + 新年）。
 *
 * 使用场景：
 * - App 打开/回到前台时，在主入口显示一次"非常吸睛"的节日庆祝弹窗。
 *
 * 规则：
 * - 每次用户打开应用时都显示（无时间限制，无每日限制）。
 */
internal object HolidayCelebrationPopupRules {

    fun shouldShowNow(): Boolean {
        // 移除所有时间限制，每次打开应用都显示
        return true
    }
}

