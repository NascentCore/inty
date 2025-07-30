package com.ai.inty.base

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.inty.utils.NetworkErrorHandler
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

open class BaseViewModel: ViewModel() {

    fun showSnackbar(text: String) {
        viewModelScope.launch {
            ToastUtils.showToast(text)
        }
    }

    /**
     * 显示网络感知的错误提示
     * 在无网络情况下不会显示错误 Toast
     * @param errorMessage 错误信息
     */
    fun showNetworkAwareError(errorMessage: String) {
        NetworkErrorHandler.handleNetworkError(
            errorMessage = errorMessage,
            showToast = { message -> showSnackbar(message) }
        )
    }

    /**
     * 处理网络异常
     * 在无网络情况下不会显示错误 Toast
     * @param exception 网络异常
     */
    fun handleNetworkException(exception: Exception) {
        NetworkErrorHandler.handleNetworkException(
            exception = exception,
            showToast = { message -> showSnackbar(message) }
        )
    }
}

open class BaseActivityViewModel : BaseViewModel() {

    private val _finishActivity = MutableStateFlow(false)
    val finishActivity = _finishActivity.asStateFlow()

    fun closeActivity(delayTimeMS: Long = 0) {
        EasyLog.log("closeActivity $this delay=$delayTimeMS")
        viewModelScope.launch(Dispatchers.Main) {
            if (delayTimeMS > 0) {
                delay(delayTimeMS)
            }
            _finishActivity.value = true
        }
    }

}