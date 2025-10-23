package com.ai.inty.base

import ai.sxwl.android.utils.ToastUtils
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.inty.utils.NetworkErrorHandler
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

    /**
     * 显示网络感知的错误提示 在无网络情况下不会显示错误 Toast
     *
     * @param errorMessage 错误信息
     * @param requestUrl 请求URL（可选）
     * @param requestMethod 请求方法（可选）
     * @param statusCode HTTP状态码（可选）
     */
    fun showNetworkAwareError(
        errorMessage: String,
        requestUrl: String? = null,
        requestMethod: String? = null,
        statusCode: Int? = null,
    ) {
        NetworkErrorHandler.handleNetworkError(
            errorMessage = errorMessage,
            showToast = { message -> ToastUtils.showShort(message) },
            requestUrl = requestUrl,
            requestMethod = requestMethod,
            statusCode = statusCode,
        )
    }

    /**
     * 处理网络异常 在无网络情况下不会显示错误 Toast
     *
     * @param exception 网络异常
     * @param requestUrl 请求URL（可选）
     * @param requestMethod 请求方法（可选）
     * @param operation 操作名称（可选）
     */
    fun handleNetworkException(
        exception: Exception,
        requestUrl: String? = null,
        requestMethod: String? = null,
        operation: String? = null,
    ) {
        NetworkErrorHandler.handleNetworkException(
            isNetworkConnected = NetworkManager.getInstance().isNetworkConnected(),
            exception = exception,
            showToast = { message -> ToastUtils.showShort(message) },
            requestUrl = requestUrl,
            requestMethod = requestMethod,
            operation = operation,
        )
    }

    /**
     * 处理 HTTP 异常并返回用户友好的错误消息
     *
     * @param e HTTP 异常
     * @param operation 操作名称，用于自定义错误消息
     * @return 用户友好的错误消息
     */
    protected fun handleHttpException(
        e: retrofit2.HttpException,
        operation: String = "operation",
    ): String {
        return when (e.code()) {
            400 -> "Invalid request parameters, please check your input"
            401 -> "Session expired, please login again"
            403 -> "Permission denied for this operation"
            404 ->
                when {
                    operation.contains("user", ignoreCase = true) -> "User information not found"
                    operation.contains("character", ignoreCase = true) ||
                            operation.contains("agent", ignoreCase = true) -> "Character not found"

                    else -> "Resource not found"
                }

            429 -> "Too many requests, please try again later"
            500 -> "Internal server error, please try again later"
            502,
            503 -> "Server temporarily unavailable, please try again later"

            else -> "Network request failed (${e.code()})"
        }
    }

    /**
     * 处理一般异常并返回用户友好的错误消息
     *
     * @param e 异常
     * @param operation 操作名称，用于自定义错误消息
     * @return 用户友好的错误消息
     */
    protected fun handleGeneralException(e: Exception, operation: String = "operation"): String {
        return when {
            e.message?.contains("timeout", ignoreCase = true) == true ->
                "Request timeout, please try again later"

            e.message?.contains("network", ignoreCase = true) == true ->
                "Network connection failed, please check your connection"

            e.message?.contains("json", ignoreCase = true) == true ->
                "Data format error, please try again later"

            else -> {
                val operationName =
                    when {
                        operation.contains("create", ignoreCase = true) -> "Creation"
                        operation.contains("update", ignoreCase = true) -> "Update"
                        operation.contains("delete", ignoreCase = true) -> "Delete"
                        operation.contains("generate", ignoreCase = true) -> "Generation"
                        else -> "Operation"
                    }
                "$operationName failed: ${e.message ?: "Unknown error"}"
            }
        }
    }
}
