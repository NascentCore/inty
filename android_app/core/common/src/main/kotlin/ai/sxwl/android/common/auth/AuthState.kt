package ai.sxwl.android.common.auth

/**
 * 认证状态
 * 只关注登录与否两种核心状态
 */
sealed class AuthState {
    /**
     * 已登录状态
     */
    data object LoggedIn : AuthState()

    /**
     * 未登录状态
     */
    data object LoggedOut : AuthState()
}

/**
 * 需要登录拦截的业务操作点
 */
enum class ProtectedAction {
    AI_GENERATION,      // AI生成功能
    PROFILE_EDIT,       // 个人资料编辑
    PREMIUM_FEATURE,    // 高级功能
    VIEW_HISTORY,       // 查看历史记录
    SYS_SETTINGS,       // 系统设置
}

/**
 * 登录拦截器回调
 */
interface LoginInterceptor {
    /**
     * 当需要登录时触发
     * @param action 触发拦截的业务操作
     */
    fun onLoginRequired(action: ProtectedAction)
}
