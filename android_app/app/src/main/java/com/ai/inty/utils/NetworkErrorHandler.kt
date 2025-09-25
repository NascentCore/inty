package com.ai.inty.utils

import com.inty.utils.log.EasyLog

/**
 * 网络错误处理工具类
 * 用于统一处理网络请求错误，避免在无网络情况下频繁显示错误提示
 */
object NetworkErrorHandler {

    /**
     * 处理网络错误，根据网络状态决定是否显示错误提示
     * @param errorMessage 原始错误信息
     * @param showToast 显示 Toast 的回调函数
     * @param logError 是否记录错误日志
     * @param requestUrl 请求URL（可选）
     * @param requestMethod 请求方法（可选）
     * @param statusCode HTTP状态码（可选）
     */
    fun handleNetworkError(
        errorMessage: String,
        showToast: (String) -> Unit,
        logError: Boolean = true,
        requestUrl: String? = null,
        requestMethod: String? = null,
        statusCode: Int? = null,
    ) {
        val networkManager = NetworkManager.getInstance()

        if (logError) {
            val logMessage = buildString {
                append("HTTP Request Failed")
                if (requestMethod != null) append(" [$requestMethod]")
                if (requestUrl != null) append(" $requestUrl")
                if (statusCode != null) append(" -> $statusCode")
                append(": $errorMessage")
            }
            EasyLog.log(logMessage, priority = EasyLog.ERROR)
        }

        // 只有在网络连接正常时才显示错误提示
        if (networkManager.shouldShowNetworkError()) {
            showToast(errorMessage)
        } else {
            // 网络未连接时，只在日志中记录，不显示 Toast
            EasyLog.log(
                "Network error suppressed (no network): $errorMessage",
                priority = EasyLog.WARN
            )
        }
    }

    /**
     * 处理网络异常，根据异常类型和网络状态决定是否显示错误提示
     * @param exception 网络异常
     * @param showToast 显示 Toast 的回调函数
     * @param logError 是否记录错误日志
     * @param requestUrl 请求URL（可选）
     * @param requestMethod 请求方法（可选）
     * @param operation 操作名称（可选）
     */
    fun handleNetworkException(
        isNetworkConnected: Boolean,
        exception: Exception,
        showToast: (String) -> Unit,
        logError: Boolean = true,
        requestUrl: String? = null,
        requestMethod: String? = null,
        operation: String? = null,
    ) {
        if (logError) {
            val logMessage = buildString {
                append("Network Exception")
                if (operation != null) append(" during $operation")
                if (requestMethod != null) append(" [$requestMethod]")
                if (requestUrl != null) append(" $requestUrl")
                append(": ${exception.message}")
            }
            EasyLog.log(logMessage, priority = EasyLog.ERROR)
            EasyLog.log(exception)
        }

        // 只有在网络连接正常时才显示错误提示
        if (isNetworkConnected) {
            val errorMessage = getErrorMessageFromException(exception)
            showToast(errorMessage)
        } else {
            // 网络未连接时，只在日志中记录，不显示 Toast
            EasyLog.log(
                "Network exception suppressed (no network): ${exception.message}",
                priority = EasyLog.WARN
            )
        }
    }

    /**
     * 根据异常类型获取用户友好的错误信息
     * @param exception 网络异常
     * @return 用户友好的错误信息
     */
    private fun getErrorMessageFromException(exception: Exception): String {
        EasyLog.log("getErrorMessageFromException = ${exception.message}")
        return when {
            exception.message?.contains("timeout", ignoreCase = true) == true ->
                "Request timeout, please try again later"

            exception.message?.contains("network", ignoreCase = true) == true ->
                "Network connection failed, please check your network settings"

            exception.message?.contains("unable to resolve host", ignoreCase = true) == true ->
                "Unable to connect to server, please check your network connection"

            exception.message?.contains("json", ignoreCase = true) == true ->
                "Data format error, please try again later"

            exception.message?.contains("connection", ignoreCase = true) == true ->
                "Connection failed, please check your network settings"

            // This is to work around the limitations of the error received from the server side.
            // As the server side does not allow enum like error cases.
            exception.message?.contains("Image generation limit reached", ignoreCase = true) == true ->
                exception.message!!

            else -> "Network request failed"
        }
    }

    /**
     * 检查是否为网络相关错误
     * @param errorMessage 错误信息
     * @return true 表示是网络相关错误
     */
    fun isNetworkRelatedError(errorMessage: String): Boolean {
        val networkKeywords = listOf(
            "timeout", "network", "connection", "unable to resolve host",
            "no route to host", "connection refused", "connection reset"
        )

        return networkKeywords.any { keyword ->
            errorMessage.contains(keyword, ignoreCase = true)
        }
    }
}
