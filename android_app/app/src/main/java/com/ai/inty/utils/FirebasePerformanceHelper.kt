package com.ai.inty.utils

import com.google.firebase.perf.FirebasePerformance
import com.google.firebase.perf.metrics.HttpMetric
import com.google.firebase.perf.metrics.Trace
import com.inty.utils.log.EasyLog
import okhttp3.Request
import okhttp3.Response

/** Firebase Performance Monitoring 工具类 提供性能追踪和网络请求监控功能 */
object FirebasePerformanceHelper {

    private val firebasePerf: FirebasePerformance?
        get() = FirebaseManager.getPerformance()

    /**
     * 开始一个自定义追踪
     *
     * @param traceName 追踪名称
     * @return Trace 对象，用于后续操作
     */
    fun startTrace(traceName: String): Trace? {
        return try {
            val perf = firebasePerf ?: return null
            val trace = perf.newTrace(traceName)
            trace.start()
            trace
        } catch (e: Exception) {
            EasyLog.log(
                "Firebase Performance: Failed to start trace '$traceName': ${e.message}",
                EasyLog.ERROR,
            )
            null
        }
    }

    /**
     * 停止追踪并记录
     *
     * @param trace Trace 对象
     */
    fun stopTrace(trace: Trace?) {
        try {
            trace?.stop()
        } catch (e: Exception) {
            EasyLog.log("Firebase Performance: Failed to stop trace: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 为追踪添加自定义属性
     *
     * @param trace Trace 对象
     * @param attributeName 属性名
     * @param value 属性值
     */
    fun putAttribute(trace: Trace?, attributeName: String, value: String) {
        try {
            trace?.putAttribute(attributeName, value)
        } catch (e: Exception) {
            EasyLog.log(
                "Firebase Performance: Failed to put attribute '$attributeName': ${e.message}",
                EasyLog.ERROR,
            )
        }
    }

    /**
     * 为追踪添加自定义指标
     *
     * @param trace Trace 对象
     * @param metricName 指标名
     * @param value 指标值
     */
    fun putMetric(trace: Trace?, metricName: String, value: Long) {
        try {
            trace?.putMetric(metricName, value)
        } catch (e: Exception) {
            EasyLog.log(
                "Firebase Performance: Failed to put metric '$metricName': ${e.message}",
                EasyLog.ERROR,
            )
        }
    }

    /**
     * 创建网络请求监控
     *
     * @param request OkHttp Request 对象
     * @return HttpMetric 对象
     */
    fun createHttpMetric(request: Request): HttpMetric? {
        return try {
            val perf = firebasePerf ?: return null
            val httpMetric = perf.newHttpMetric(request.url.toString(), request.method)
            httpMetric
        } catch (e: Exception) {
            EasyLog.log(
                "Firebase Performance: Failed to create HTTP metric: ${e.message}",
                EasyLog.ERROR,
            )
            null
        }
    }

    /**
     * 开始网络请求监控
     *
     * @param httpMetric HttpMetric 对象
     */
    fun startHttpMetric(httpMetric: HttpMetric?) {
        try {
            httpMetric?.start()
        } catch (e: Exception) {
            EasyLog.log(
                "Firebase Performance: Failed to start HTTP metric: ${e.message}",
                EasyLog.ERROR,
            )
        }
    }

    /**
     * 停止网络请求监控
     *
     * @param httpMetric HttpMetric 对象
     * @param response OkHttp Response 对象
     */
    fun stopHttpMetric(httpMetric: HttpMetric?, response: Response?) {
        try {
            // Firebase Performance HttpMetric 会自动记录响应信息
            httpMetric?.stop()
        } catch (e: Exception) {
            EasyLog.log(
                "Firebase Performance: Failed to stop HTTP metric: ${e.message}",
                EasyLog.ERROR,
            )
        }
    }

    /**
     * 便捷方法：执行带性能监控的操作
     *
     * @param traceName 追踪名称
     * @param operation 要执行的操作
     * @return 操作结果
     */
    inline fun <T> trace(traceName: String, operation: (Trace?) -> T): T {
        val trace = startTrace(traceName)
        return try {
            operation(trace)
        } finally {
            stopTrace(trace)
        }
    }
}
