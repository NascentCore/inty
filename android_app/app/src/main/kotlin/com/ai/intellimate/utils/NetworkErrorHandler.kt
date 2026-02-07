package com.ai.intellimate.utils

import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import kotlinx.coroutines.CancellationException

/** 网络错误处理器 负责处理网络相关的错误提示和异常处理 */
object NetworkErrorHandler {

    // #region agent log（仅上报 Crashlytics，便于用户端复现时在 Firebase 查看）
    /** 用户端无法复现时：将 TLS/parse 错误上报 Crashlytics（非致命），便于在 Firebase 控制台查看 hypothesisId、location、设备等 */
    private fun reportTlsParseToFirebase(hypothesisId: String, location: String, errorMessage: String) {
        try {
            val safeMsg = errorMessage.take(200).replace("\"", "'")
            FirebaseManager.recordException(
                Exception("TLS_PARSE_ERROR [hypothesisId=$hypothesisId] $location"),
                mapOf(
                    "tls_parse_hypothesis_id" to hypothesisId,
                    "tls_parse_location" to location.take(100),
                    "tls_parse_message" to safeMsg,
                ),
            )
        } catch (_: Exception) { }
    }

    private fun reportTlsParseIfRelevant(hypothesisId: String, source: String, errorMessage: String) {
        if (!errorMessage.contains("TLS", ignoreCase = true) && !errorMessage.contains("parse", ignoreCase = true)) return
        reportTlsParseToFirebase(hypothesisId, "NetworkErrorHandler.kt:$source", errorMessage)
    }

    /** 供其他模块埋点：当 message 含 TLS/parse 时上报 Crashlytics（hypothesisId C/D/E/F/G/H） */
    fun writeTlsParseDebugLogIfRelevant(hypothesisId: String, location: String, message: String?) {
        if (message.isNullOrBlank()) return
        if (!message.contains("TLS", ignoreCase = true) && !message.contains("parse", ignoreCase = true)) return
        reportTlsParseToFirebase(hypothesisId, location, message)
    }
    // #endregion

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
        // #region agent log
        reportTlsParseIfRelevant("A", "showNetworkAwareError", errorMessage)
        // #endregion
        // 检查是否为取消操作，如果是则不显示toast
        if (
            errorMessage.contains("cancelled", ignoreCase = true) ||
                errorMessage.contains("cancel", ignoreCase = true)
        ) {
            LogUtils.d("网络请求被取消: $requestUrl")
            return
        }

        // 显示错误消息
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
        // 检查是否为取消异常，如果是则不显示toast
        if (exception is CancellationException) {
            LogUtils.d("网络请求被取消: $requestUrl")
            return "Request cancelled"
        }

        val errorMessage = exception.message ?: "Network error occurred"

        // #region agent log
        reportTlsParseIfRelevant("B", "handleNetworkException", errorMessage)
        // #endregion
        // 检查错误消息是否包含取消相关词汇
        if (
            errorMessage.contains("cancelled", ignoreCase = true) ||
                errorMessage.contains("cancel", ignoreCase = true)
        ) {
            LogUtils.d("网络请求被取消: $requestUrl - $errorMessage")
            return errorMessage
        }

        // 显示错误消息
        ToastUtils.showShort(errorMessage)
        return errorMessage
    }
}
