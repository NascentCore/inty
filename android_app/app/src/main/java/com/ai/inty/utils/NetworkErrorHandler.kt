package com.ai.inty.utils

import ai.sxwl.android.utils.ToastUtils

/**
 * 网络错误处理器
 * 负责处理网络相关的错误提示和异常处理
 */
object NetworkErrorHandler {

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
        // 直接显示错误消息
        ToastUtils.showShort(errorMessage)
    }

    /**
     * 处理网络异常 在无网络情况下不会显示错误 Toast
     *
     * @param exception 网络异常
     * @param requestUrl 请求URL（可选）
     * @param requestMethod 请求方法（可选）
     * @param operation 操作名称（可选）
     * @return 错误消息
     */
    fun handleNetworkException(
        exception: Exception,
        requestUrl: String? = null,
        requestMethod: String? = null,
        operation: String? = null,
    ): String {
        val errorMessage = exception.message ?: "Network error occurred"
        // 直接显示错误消息
        ToastUtils.showShort(errorMessage)
        return errorMessage
    }
}