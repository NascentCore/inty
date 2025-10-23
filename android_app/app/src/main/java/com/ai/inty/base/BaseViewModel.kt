package com.ai.inty.base

import ai.sxwl.android.utils.ToastUtils
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.inty.utils.NetworkManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch

open class BaseViewModel : ViewModel() {

    // 事件通知机制
    private val _events = MutableSharedFlow<ViewModelEvent>()
    val events: SharedFlow<ViewModelEvent> = _events.asSharedFlow()

    /**
     * 发送事件通知
     */
    protected fun sendEvent(event: ViewModelEvent) {
        viewModelScope.launch {
            _events.emit(event)
        }
    }

    /** 附带网络检查的launch */
    fun launchWithNetCheck(block: suspend () -> Unit) =
        viewModelScope.launch(Dispatchers.IO) {
            // 检查网络连接
            val networkManager = NetworkManager.getInstance()
            if (!networkManager.isNetworkConnected()) {
                ToastUtils.showShort("Please check your network connection")
                return@launch
            }
            runCatching { block() }.onFailure { it.printStackTrace() }
        }


}
