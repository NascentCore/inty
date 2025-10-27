package com.example.firebaselogging

import android.content.Context
import android.util.Log
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.crashlytics.FirebaseCrashlytics
import com.google.firebase.perf.FirebasePerformance
import com.google.firebase.perf.metrics.Trace
import java.text.SimpleDateFormat
import java.util.*

/**
 * Firebase 日志管理类
 * 负责统一管理 Firebase Analytics、Crashlytics 和 Performance Monitoring
 */
class LoggingManager private constructor(context: Context) {
    
    private val firebaseAnalytics: FirebaseAnalytics = FirebaseAnalytics.getInstance(context)
    private val crashlytics: FirebaseCrashlytics = FirebaseCrashlytics.getInstance()
    private val performance: FirebasePerformance = FirebasePerformance.getInstance()
    
    // 日志输出回调
    private var logCallback: ((String) -> Unit)? = null
    
    companion object {
        @Volatile
        private var INSTANCE: LoggingManager? = null
        
        fun getInstance(context: Context): LoggingManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: LoggingManager(context.applicationContext).also { INSTANCE = it }
            }
        }
    }
    
    /**
     * 设置日志输出回调
     */
    fun setLogCallback(callback: (String) -> Unit) {
        this.logCallback = callback
    }
    
    /**
     * 记录基础事件
     */
    fun logEvent(eventName: String, parameters: Map<String, Any> = emptyMap()) {
        try {
            val bundle = android.os.Bundle().apply {
                parameters.forEach { (key, value) ->
                    when (value) {
                        is String -> putString(key, value)
                        is Int -> putInt(key, value)
                        is Long -> putLong(key, value)
                        is Double -> putDouble(key, value)
                        is Float -> putFloat(key, value)
                        is Boolean -> putBoolean(key, value)
                        else -> putString(key, value.toString())
                    }
                }
            }
            
            firebaseAnalytics.logEvent(eventName, bundle)
            
            val logMessage = "[${getCurrentTime()}] 事件记录: $eventName, 参数: $parameters"
            logToOutput(logMessage)
            Log.d(TAG, logMessage)
            
        } catch (e: Exception) {
            val errorMessage = "[${getCurrentTime()}] 记录事件失败: $eventName, 错误: ${e.message}"
            logToOutput(errorMessage)
            Log.e(TAG, errorMessage, e)
        }
    }
    
    /**
     * 记录自定义事件
     */
    fun logCustomEvent(eventName: String, eventValue: String) {
        val parameters = mapOf(
            LogEvent.PARAM_EVENT_NAME to eventName,
            LogEvent.PARAM_EVENT_VALUE to eventValue,
            LogEvent.PARAM_TIMESTAMP to System.currentTimeMillis()
        )
        logEvent(LogEvent.EVENT_CUSTOM_EVENT, parameters)
    }
    
    /**
     * 设置用户属性
     */
    fun setUserProperty(key: String, value: String) {
        try {
            firebaseAnalytics.setUserProperty(key, value)
            
            val logMessage = "[${getCurrentTime()}] 用户属性设置: $key = $value"
            logToOutput(logMessage)
            Log.d(TAG, logMessage)
            
        } catch (e: Exception) {
            val errorMessage = "[${getCurrentTime()}] 设置用户属性失败: $key = $value, 错误: ${e.message}"
            logToOutput(errorMessage)
            Log.e(TAG, errorMessage, e)
        }
    }
    
    /**
     * 设置用户ID
     */
    fun setUserId(userId: String) {
        try {
            firebaseAnalytics.setUserId(userId)
            crashlytics.setUserId(userId)
            
            val logMessage = "[${getCurrentTime()}] 用户ID设置: $userId"
            logToOutput(logMessage)
            Log.d(TAG, logMessage)
            
        } catch (e: Exception) {
            val errorMessage = "[${getCurrentTime()}] 设置用户ID失败: $userId, 错误: ${e.message}"
            logToOutput(errorMessage)
            Log.e(TAG, errorMessage, e)
        }
    }
    
    /**
     * 记录按钮点击事件
     */
    fun logButtonClick(buttonName: String) {
        val parameters = mapOf(
            LogEvent.PARAM_BUTTON_NAME to buttonName,
            LogEvent.PARAM_TIMESTAMP to System.currentTimeMillis()
        )
        logEvent(LogEvent.EVENT_BUTTON_CLICKED, parameters)
    }
    
    /**
     * 触发测试崩溃
     */
    fun triggerTestCrash() {
        try {
            val logMessage = "[${getCurrentTime()}] 触发测试崩溃"
            logToOutput(logMessage)
            Log.d(TAG, logMessage)
            
            // 记录崩溃前的信息
            crashlytics.setCustomKey("crash_triggered_at", getCurrentTime())
            crashlytics.setCustomKey("test_crash", true)
            
            // 触发崩溃
            throw RuntimeException("这是一个测试崩溃 - 用于验证 Firebase Crashlytics 功能")
            
        } catch (e: Exception) {
            val errorMessage = "[${getCurrentTime()}] 触发崩溃失败: ${e.message}"
            logToOutput(errorMessage)
            Log.e(TAG, errorMessage, e)
        }
    }
    
    /**
     * 记录性能事件
     */
    fun logPerformanceEvent(traceName: String, duration: Long) {
        try {
            val trace = performance.newTrace(traceName)
            trace.start()
            
            // 模拟一些工作
            Thread.sleep(duration)
            
            trace.stop()
            
            val logMessage = "[${getCurrentTime()}] 性能事件记录: $traceName, 耗时: ${duration}ms"
            logToOutput(logMessage)
            Log.d(TAG, logMessage)
            
        } catch (e: Exception) {
            val errorMessage = "[${getCurrentTime()}] 记录性能事件失败: $traceName, 错误: ${e.message}"
            logToOutput(errorMessage)
            Log.e(TAG, errorMessage, e)
        }
    }
    
    /**
     * 记录应用启动事件
     */
    fun logAppOpened() {
        val parameters = mapOf(
            LogEvent.PARAM_TIMESTAMP to System.currentTimeMillis(),
            LogEvent.PARAM_APP_VERSION to "1.0.0"
        )
        logEvent(LogEvent.EVENT_APP_OPENED, parameters)
    }
    
    /**
     * 记录错误日志
     */
    fun logError(error: String, throwable: Throwable? = null) {
        try {
            crashlytics.log(error)
            if (throwable != null) {
                crashlytics.recordException(throwable)
            }
            
            val logMessage = "[${getCurrentTime()}] 错误记录: $error"
            logToOutput(logMessage)
            Log.e(TAG, logMessage, throwable)
            
        } catch (e: Exception) {
            val errorMessage = "[${getCurrentTime()}] 记录错误失败: $error, 错误: ${e.message}"
            logToOutput(errorMessage)
            Log.e(TAG, errorMessage, e)
        }
    }
    
    /**
     * 设置自定义键值对（用于 Crashlytics）
     */
    fun setCustomKey(key: String, value: String) {
        try {
            crashlytics.setCustomKey(key, value)
            
            val logMessage = "[${getCurrentTime()}] 自定义键设置: $key = $value"
            logToOutput(logMessage)
            Log.d(TAG, logMessage)
            
        } catch (e: Exception) {
            val errorMessage = "[${getCurrentTime()}] 设置自定义键失败: $key = $value, 错误: ${e.message}"
            logToOutput(errorMessage)
            Log.e(TAG, errorMessage, e)
        }
    }
    
    /**
     * 输出日志到界面
     */
    private fun logToOutput(message: String) {
        logCallback?.invoke(message)
    }
    
    /**
     * 获取当前时间字符串
     */
    private fun getCurrentTime(): String {
        val sdf = SimpleDateFormat("HH:mm:ss.SSS", Locale.getDefault())
        return sdf.format(Date())
    }
    
    companion object {
        private const val TAG = "LoggingManager"
    }
}