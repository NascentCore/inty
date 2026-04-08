package com.ai.core.data.exceptions

import com.ai.core.data.exceptions.GlobalErrorHandler.sendError
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.receiveAsFlow

object GlobalErrorHandler {
    private val _error = Channel<Exception?>(10)

    val error = _error.receiveAsFlow()

    fun sendError(exception: Exception) {
        _error.trySend(exception)
    }
}

/**
 * 全部捕获异常，参考runCatch
 */
inline fun globalCatch(block: () -> Unit) {
    try {
        block()
    } catch (e: Exception) {
        sendError(e)
    }
}