package com.ai.intellimate.utils

import ai.sxwl.android.data.store.IntySetting
import android.content.Context
import com.ai.intellimate.login.LoginActivity

/** Guest用户登录限制工具 用于在特定操作时检查用户状态并引导登录 */
object GuestLoginLimiter {

    /**
     * 检查是否需要登录限制
     *
     * @return true表示需要限制（guest用户），false表示不需要限制（已登录用户）
     */
    fun shouldLimitGuest(): Boolean {
        return IntySetting.isLogin() && IntySetting.isGuestUser()
    }

    /**
     * 检查是否为已登录的正式用户
     *
     * @return true表示是正式用户，false表示是guest用户或未登录
     */
    fun isFormalUser(): Boolean {
        return IntySetting.isLogin() && !IntySetting.isGuestUser()
    }

    /**
     * 如果需要限制，则跳转到登录页面
     *
     * @param context 上下文
     * @return true表示已跳转登录，false表示不需要跳转
     */
    fun checkAndNavigateToLogin(context: Context): Boolean {
        return if (shouldLimitGuest()) {
            LoginActivity.launch(context)
            true
        } else {
            false
        }
    }

    /**
     * 检查滑动位置是否需要登录限制
     *
     * @param currentIndex 当前滑动到的索引
     * @param pageSize 每页大小
     * @return true表示需要限制
     */
    fun shouldLimitScroll(currentIndex: Int, pageSize: Int = 20): Boolean {
        if (!shouldLimitGuest()) return false

        // 每滑动5个agent检查一次
        val checkInterval = 5
        val shouldCheck = (currentIndex + 1) % checkInterval == 0

        // 滑动到第20个时强制限制
        val isAtPageEnd = currentIndex >= pageSize - 1

        return shouldCheck || isAtPageEnd
    }
}
