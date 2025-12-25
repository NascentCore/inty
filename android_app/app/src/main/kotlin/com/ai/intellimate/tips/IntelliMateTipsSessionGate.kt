package com.ai.intellimate.tips

/**
 * CREATED_BY_AGENT: cursor-gpt-5.2
 *
 * “每个 session 只展示一次 tips 弹窗”的门控状态。
 *
 * 注意：session 的定义由 [IntelliMateTipsForegroundSessionTracker] 提供（前台 -> 后台）。
 */
object IntelliMateTipsSessionGate {

    @Volatile private var hasShownInSession: Boolean = false
    @Volatile private var isLoadingOrShowing: Boolean = false

    fun tryAcquireToShowInCurrentSession(): Boolean {
        if (hasShownInSession) return false
        if (isLoadingOrShowing) return false
        isLoadingOrShowing = true
        return true
    }

    fun markShownInCurrentSession() {
        hasShownInSession = true
        isLoadingOrShowing = false
    }

    fun releaseWithoutShowing() {
        isLoadingOrShowing = false
    }

    fun resetForNewSession() {
        hasShownInSession = false
        isLoadingOrShowing = false
    }
}
