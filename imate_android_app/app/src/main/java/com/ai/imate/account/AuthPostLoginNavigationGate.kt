package com.ai.imate.account

import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * 登录成功后 [isLogin] 会先变为 true，但需继续在 [AuthLoadingScreen] 完成最短展示与收尾动画后再切主流程。
 * 为 true 时 [MainViewModel] 仍停留在 Login 根路由，避免 Compose 提前卸掉加载页。
 */
@Singleton
class AuthPostLoginNavigationGate @Inject constructor() {
    private val _holdPostLoginNavigation = MutableStateFlow(false)
    val holdPostLoginNavigation: StateFlow<Boolean> = _holdPostLoginNavigation.asStateFlow()

    fun beginHold() {
        _holdPostLoginNavigation.value = true
    }

    fun releaseHold() {
        _holdPostLoginNavigation.value = false
    }
}
