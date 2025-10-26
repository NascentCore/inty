package com.ai.intellimate.utils

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
    fun handleGeneralException(e: Exception, operation: String = "operation"): String {
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
