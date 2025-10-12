package com.ai.inty.utils

import android.content.Context
import com.inty.utils.log.EasyLog
import java.lang.Thread.UncaughtExceptionHandler

/** 全局异常处理器 捕获未处理的异常并记录到 Firebase Crashlytics */
class GlobalExceptionHandler(
    private val context: Context,
    private val defaultHandler: UncaughtExceptionHandler?,
) : UncaughtExceptionHandler {

    override fun uncaughtException(thread: Thread, exception: Throwable) {
        try {
            // 记录异常发生时的上下文信息
            recordCrashContext(thread, exception)

            // 记录到 Firebase Crashlytics
            FirebaseManager.recordException(exception)

            // 记录到本地日志
            EasyLog.log(
                "GlobalExceptionHandler: Uncaught exception in thread ${thread.name}",
                EasyLog.ERROR,
            )
            EasyLog.log("Exception: ${exception.message}", EasyLog.ERROR)
            exception.printStackTrace()
        } catch (e: Exception) {
            EasyLog.log("Failed to handle global exception: ${e.message}", EasyLog.ERROR)
        } finally {
            // 调用默认处理器
            defaultHandler?.uncaughtException(thread, exception)
        }
    }

    private fun recordCrashContext(thread: Thread, exception: Throwable) {
        try {
            // 记录线程信息
            FirebaseManager.setCustomKey("crash_thread_name", thread.name)
            FirebaseManager.setCustomKey("crash_thread_id", thread.id.toString())
            FirebaseManager.setCustomKey("crash_thread_priority", thread.priority.toString())

            // 记录异常信息
            FirebaseManager.setCustomKey("crash_exception_type", exception.javaClass.simpleName)
            FirebaseManager.setCustomKey("crash_exception_message", exception.message ?: "unknown")

            // 记录当前页面信息
            val pageInfo = PageTrackingHelper.getCurrentPageInfo()
            pageInfo.forEach { (key, value) ->
                FirebaseManager.setCustomKey("crash_$key", value.toString())
            }

            // 记录应用状态
            FirebaseManager.setCustomKey("crash_timestamp", System.currentTimeMillis().toString())
            FirebaseManager.setCustomKey("crash_memory_usage", getMemoryUsage())

            EasyLog.log("Crash context recorded successfully")
        } catch (e: Exception) {
            EasyLog.log("Failed to record crash context: ${e.message}", EasyLog.ERROR)
        }
    }

    private fun getMemoryUsage(): String {
        return try {
            val runtime = Runtime.getRuntime()
            val usedMemory = runtime.totalMemory() - runtime.freeMemory()
            val maxMemory = runtime.maxMemory()
            "${usedMemory / 1024 / 1024}MB / ${maxMemory / 1024 / 1024}MB"
        } catch (e: Exception) {
            "unknown"
        }
    }

    companion object {
        /** 安装全局异常处理器 */
        fun install(context: Context) {
            val defaultHandler = Thread.getDefaultUncaughtExceptionHandler()
            val globalHandler = GlobalExceptionHandler(context, defaultHandler)
            Thread.setDefaultUncaughtExceptionHandler(globalHandler)
            EasyLog.log("GlobalExceptionHandler installed")
        }
    }
}
