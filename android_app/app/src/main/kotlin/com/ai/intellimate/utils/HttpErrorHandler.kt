package com.ai.intellimate.utils

import ai.sxwl.android.utils.LogUtils
import androidx.annotation.StringRes
import com.ai.intellimate.R
import retrofit2.HttpException

/** HTTP 错误处理器 负责处理 HTTP 异常并返回用户友好的错误消息 */
object HttpErrorHandler {

    /**
     * 处理 HTTP 异常并返回用户友好的错误消息
     *
     * @param e HTTP 异常
     * @param operation 操作名称，用于自定义错误消息
     * @return 用户友好的错误消息
     */
    fun handleHttpException(
        e: HttpException,
        operation: String = "operation",
    ): String {
        return when (e.code()) {
            400 -> getString(R.string.http_error_invalid_request_parameters)
            401 -> getString(R.string.http_error_session_expired)
            403 -> getString(R.string.http_error_permission_denied)
            404 ->
                when {
                    operation.contains("user", ignoreCase = true) -> getString(R.string.http_error_user_not_found)
                    operation.contains("character", ignoreCase = true) ||
                        operation.contains("agent", ignoreCase = true) -> getString(R.string.http_error_character_not_found)
                    else -> getString(R.string.http_error_resource_not_found)
                }
            429 -> getString(R.string.http_error_too_many_requests)
            500 -> getString(R.string.http_error_internal_server_error)
            502,
            503 -> getString(R.string.http_error_server_unavailable)
            else -> getString(R.string.http_error_network_request_failed_with_code, e.code())
        }
    }

    /**
     * 处理一般异常并返回用户友好的错误消息
     *
     * @param e 异常
     * @param operation 操作名称，用于自定义错误消息
     * @return 用户友好的错误消息
     */
    fun handleGeneralException(e: Exception, operation: String = "operation"): String {
        return when {
            e.message?.contains("timeout", ignoreCase = true) == true ->
                getString(R.string.http_error_request_timeout)
            e.message?.contains("network", ignoreCase = true) == true ->
                getString(R.string.http_error_network_connection_failed)
            e.message?.contains("json", ignoreCase = true) == true ->
                getString(R.string.http_error_data_format_error)
            else -> {
                val operationName =
                    when {
                        operation.contains("create", ignoreCase = true) -> getString(R.string.http_error_creation_failed_with_message, e.message ?: getString(R.string.http_error_unknown_error))
                        operation.contains("update", ignoreCase = true) -> getString(R.string.http_error_update_failed_with_message, e.message ?: getString(R.string.http_error_unknown_error))
                        operation.contains("delete", ignoreCase = true) -> getString(R.string.http_error_delete_failed_with_message, e.message ?: getString(R.string.http_error_unknown_error))
                        operation.contains("generate", ignoreCase = true) -> getString(R.string.http_error_generation_failed_with_message, e.message ?: getString(R.string.http_error_unknown_error))
                        else -> getString(R.string.http_error_operation_failed_with_message, e.message ?: getString(R.string.http_error_unknown_error))
                    }
                operationName
            }
        }
    }

    /** 获取字符串资源 */
    private fun getString(@StringRes resId: Int): String {
        return try {
            val context = ai.sxwl.android.utils.Utils.getApp()
            context.getString(resId)
        } catch (e: Exception) {
            LogUtils.e("获取字符串资源失败: $resId", e)
            "Unknown"
        }
    }

    /** 获取带参数的字符串资源 */
    private fun getString(@StringRes resId: Int, vararg formatArgs: Any?): String {
        return try {
            val context = ai.sxwl.android.utils.Utils.getApp()
            context.getString(resId, *formatArgs)
        } catch (e: Exception) {
            LogUtils.e("获取字符串资源失败: $resId", e)
            "Unknown"
        }
    }
}
