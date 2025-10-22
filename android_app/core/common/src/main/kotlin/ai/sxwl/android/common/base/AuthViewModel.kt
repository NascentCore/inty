package ai.sxwl.android.common.base

import ai.sxwl.android.common.auth.AuthManager
import ai.sxwl.android.common.auth.AuthState
import ai.sxwl.android.common.auth.LoginInterceptor
import ai.sxwl.android.common.auth.ProtectedAction
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

/**
 * 具有认证感知能力的ViewModel
 * 在BaseViewModel基础上集成认证逻辑
 *
 * @param IState 状态类型，建议包含登录相关状态
 * @param IIntent 意图类型
 * @param IEvent 事件类型，建议包含登录相关事件
 */
abstract class AuthViewModel<IState : BaseMVI.IState, IIntent : BaseMVI.IIntent, IEvent : BaseMVI.IEvent> :
    BaseViewModel<IState, IIntent, IEvent>(), LoginInterceptor {

    /**
     * 认证状态流
     */
    val authState: StateFlow<AuthState> = AuthManager.authState

    init {
        // 设置登录拦截器
        AuthManager.setLoginInterceptor(this)

        // 监听认证状态变化
        launchUI {
            authState.collect { state ->
                onAuthStateChanged(state)
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        // 移除登录拦截器
        AuthManager.removeLoginInterceptor(this)
    }

    /**
     * 检查是否已登录
     */
    protected fun isLoggedIn(): Boolean = AuthManager.isLoggedIn()


    /**
     * 登录成功处理
     */
    protected fun onLoginSuccess(token: String) {
        viewModelScope.launch {

        }
    }

    /**
     * 登出处理
     */
    protected fun logout() {
        viewModelScope.launch {
            AuthManager.logout()
        }
    }

    /**
     * 认证状态变化回调
     * 子类可重写此方法来响应登录状态变化
     */
    protected open fun onAuthStateChanged(authState: AuthState) {
        // 默认实现：什么都不做
        // 子类可以重写来更新UI状态
    }

    /**
     * 登录拦截回调实现
     * 子类必须实现此方法来处理登录需求
     */
    abstract override fun onLoginRequired(action: ProtectedAction)
}
