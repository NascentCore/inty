package ai.sxwl.android.common.base

import ai.sxwl.android.common.auth.AuthManager
import ai.sxwl.android.common.auth.ProtectedAction
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * ViewModel基类（符合MVVM/MVI架构）
 * 提供统一的登录拦截和状态管理能力
 *
 * 用户操作 → Intent → ViewModel → 业务逻辑 → State更新 → UI重组
 *                                      ↓
 *                                Event发射 → 副作用处理
 */
abstract class BaseViewModel<IState : BaseMVI.IState, IIntent : BaseMVI.IIntent, IEvent : BaseMVI.IEvent> :
    BaseVM() {

    private val _state = MutableStateFlow(createInitialState())
    val state: StateFlow<IState> = _state.asStateFlow()

    private val _events = MutableStateFlow<IEvent?>(null)
    val events: StateFlow<IEvent?> = _events.asStateFlow()

    /**
     * 创建初始状态
     */
    abstract fun createInitialState(): IState

    /**
     * 处理意图
     */
    abstract suspend fun processIntent(intent: IIntent)

    /**
     * 更新状态
     */
    protected fun updateState(update: (IState) -> IState) {
        _state.value = update(_state.value)
    }

    /**
     * 发送事件
     */
    protected fun sendEvent(event: IEvent) {
        _events.value = event
    }

    /**
     * 清除事件
     */
    fun clearEvent() {
        _events.value = null
    }

    /**
     * 执行需要登录的操作
     */
    protected fun executeWithAuth(
        action: ProtectedAction,
        operation: () -> Unit,
    ): Boolean {
        return AuthManager.executeWithAuth(action, operation)
    }

    /**
     * 执行需要登录的挂起操作
     */
    protected suspend fun executeWithAuthSuspend(
        action: ProtectedAction,
        operation: suspend () -> Unit,
    ): Boolean {
        return AuthManager.executeWithAuthSuspend(action, operation)
    }

    /**
     * 处理意图（便捷方法）
     */
    fun handleIntent(intent: IIntent) {
        launchUI {
            processIntent(intent)
        }
    }
}

object BaseMVI {
    interface IState
    interface IIntent
    interface IEvent
}
