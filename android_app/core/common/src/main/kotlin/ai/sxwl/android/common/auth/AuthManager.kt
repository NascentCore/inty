package ai.sxwl.android.common.auth

import ai.sxwl.android.utils.LogUtils
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 现代化认证管理器
 * 专注于登录状态管理和业务操作拦截，与data模块深度集成
 *
 * 认证逻辑：
 * 1. 未登录用户 -> 需要登录成为正式用户
 * 2. Guest用户 -> 需要登录成为正式用户
 * 3. 正式用户 -> 可以访问所有ProtectedAction
 */
object AuthManager {

    //定义当前操作所使用的异步协程的
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    //当前认证状态，默认为未登录/已登出
    private val _authState = MutableStateFlow<AuthState>(AuthState.LoggedOut)
    val authState: StateFlow<AuthState> = _authState.asStateFlow()

    //登录拦截器列表，支持多个拦截器
    private val loginInterceptors = mutableListOf<LoginInterceptor>()

    // 缓存用户状态，避免在非挂起函数中使用异步操作
    private var isGuestUser: Boolean = true //当前用户是否是guest

    // 需要正式用户权限的业务操作
    private val protectedActions = setOf(
        ProtectedAction.AI_GENERATION,
        ProtectedAction.PROFILE_EDIT,
        ProtectedAction.PREMIUM_FEATURE,
        ProtectedAction.VIEW_HISTORY,
        ProtectedAction.SYS_SETTINGS,
    )

    /**
     * 初始化认证管理器
     */
    fun initialize() {

    }

    /**
     * 强制刷新用户状态
     */
    suspend fun refreshUserState() {

    }

    /**
     * 强制刷新用户状态（同步版本）
     */
    fun refreshUserStateSync() {
        scope.launch {
            refreshUserState()
        }
    }


    /**
     * 设置登录拦截器
     */
    fun setLoginInterceptor(interceptor: LoginInterceptor) {
        if (!loginInterceptors.contains(interceptor)) {
            loginInterceptors.add(interceptor)
            LogUtils.d("添加登录拦截器: ${interceptor.javaClass.simpleName}")
        }
    }

    /**
     * 移除登录拦截器
     */
    fun removeLoginInterceptor(interceptor: LoginInterceptor) {
        loginInterceptors.remove(interceptor)
        LogUtils.d("移除登录拦截器: ${interceptor.javaClass.simpleName}")
    }

    /**
     * 检查是否已登录
     */
    fun isLoggedIn(): Boolean = _authState.value is AuthState.LoggedIn

    /**
     * 检查是否为正式用户（非Guest用户）
     */
    suspend fun isFormalUser(): Boolean {
        return runCatching {
            // 使用本地缓存检查
            false
        }.getOrElse { false }
    }

    /**
     * 同步检查是否为正式用户（使用缓存）
     */
    fun isFormalUserSync(): Boolean {
        return !isGuestUser
    }

    /**
     * 执行需要登录验证的操作
     *
     * 认证逻辑：
     * 1. 未登录 -> 需要登录
     * 2. Guest用户 -> 需要登录成为正式用户
     * 3. 正式用户 -> 允许执行操作
     */
    fun executeWithAuth(action: ProtectedAction, operation: () -> Unit): Boolean {
        return if (requiresLogin(action)) {
            val isLoggedIn = isLoggedIn()//是否已经登录
            val isFormalUser = isFormalUserSync()//是否是正式用户（非Guest）

            LogUtils.d("认证检查 - 操作: $action, 已登录: $isLoggedIn, 正式用户: $isFormalUser, loginInterceptors数量: ${loginInterceptors.size}")

            if (!isLoggedIn) {// 未登录，需要登录
                LogUtils.w("认证失败 - 未登录，操作: $action")
                loginInterceptors.forEach { it.onLoginRequired(action) }
                false
            } else if (!isFormalUser) {
                // 已登录但为Guest用户，需要升级为正式用户
                LogUtils.w("认证失败 - Guest用户需要升级为正式用户，操作: $action")
                loginInterceptors.forEach { it.onLoginRequired(action) }
                false
            } else {
                // 已登录且为正式用户，允许执行操作
                LogUtils.d("认证通过 - 正式用户，执行操作: $action")
                operation()
                true
            }
        } else {
            LogUtils.d("操作不需要登录验证: $action")
            operation()
            true
        }
    }

    /**
     * 执行需要登录验证的挂起操作
     *
     * 认证逻辑：
     * 1. 未登录 -> 需要登录
     * 2. Guest用户 -> 需要登录成为正式用户
     * 3. 正式用户 -> 允许执行操作
     */
    suspend fun executeWithAuthSuspend(
        action: ProtectedAction,
        operation: suspend () -> Unit
    ): Boolean {
        return if (requiresLogin(action)) {
            val isLoggedIn = isLoggedIn()
            val isFormalUser = isFormalUser()

            LogUtils.d("认证检查(挂起) - 操作: $action, 已登录: $isLoggedIn, 正式用户: $isFormalUser")

            when {
                // 未登录，需要登录
                !isLoggedIn -> {
                    LogUtils.w("认证失败(挂起) - 未登录，操作: $action")
                    loginInterceptors.forEach { it.onLoginRequired(action) }
                    false
                }
                // 已登录但为Guest用户，需要升级为正式用户
                isLoggedIn && !isFormalUser -> {
                    LogUtils.w("认证失败(挂起) - Guest用户需要升级为正式用户，操作: $action")
                    loginInterceptors.forEach { it.onLoginRequired(action) }
                    false
                }
                // 已登录且为正式用户，允许执行操作
                else -> {
                    LogUtils.d("认证通过(挂起) - 正式用户，执行操作: $action")
                    operation()
                    true
                }
            }
        } else {
            LogUtils.d("操作不需要登录验证(挂起): $action")
            operation()
            true
        }
    }

    /**
     * 仅正式用户登录成功后，需要更新auth的管理状态
     */
    suspend fun loginSuccess() {
        LogUtils.d("用户登录成功，更新认证状态")
        _authState.emit(AuthState.LoggedIn)
    }

    /**
     * 登出
     */
    suspend fun logout() {
        LogUtils.d("用户登出，更新认证状态")
        _authState.emit(AuthState.LoggedOut)
    }

    /**
     * 检查操作是否需要登录
     */
    private fun requiresLogin(action: ProtectedAction): Boolean {
        return protectedActions.contains(action)
    }

}
