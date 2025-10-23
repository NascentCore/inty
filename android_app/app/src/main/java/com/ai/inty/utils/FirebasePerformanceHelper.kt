package com.ai.inty.utils

import ai.sxwl.android.utils.LogUtils
import com.google.firebase.perf.FirebasePerformance
import com.google.firebase.perf.metrics.HttpMetric
import com.google.firebase.perf.metrics.Trace
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
            LogUtils.e("Firebase Performance: Failed to start trace '$traceName': ${e.message}")
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
            LogUtils.e("Firebase Performance: Failed to stop trace: ${e.message}")
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
            LogUtils.e("Firebase Performance: Failed to put attribute '$attributeName': ${e.message}")
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
            LogUtils.e("Firebase Performance: Failed to put metric '$metricName': ${e.message}")
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

            // 设置请求属性
            try {
                // 设置用户代理
                val userAgent = request.header("User-Agent")
                if (!userAgent.isNullOrEmpty()) {
                    httpMetric.putAttribute("user_agent", userAgent)
                }

                // 设置请求类型
                httpMetric.putAttribute("request_type", "api_call")

                // 设置端点信息
                val path = request.url.encodedPath
                if (!path.isNullOrEmpty()) {
                    httpMetric.putAttribute("endpoint", path)
                }
            } catch (e: Exception) {
                LogUtils.w("Firebase Performance: Failed to set HTTP metric attributes: ${e.message}")
            }

            httpMetric
        } catch (e: Exception) {
            LogUtils.e("Firebase Performance: Failed to create HTTP metric: ${e.message}")
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
            LogUtils.e("Firebase Performance: Failed to start HTTP metric: ${e.message}")
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
            if (httpMetric != null) {
                // 设置响应码
                if (response != null) {
                    httpMetric.setHttpResponseCode(response.code)

                    // 设置响应大小（如果可用）
                    val contentLength = response.header("Content-Length")
                    if (!contentLength.isNullOrEmpty()) {
                        try {
                            httpMetric.setResponsePayloadSize(contentLength.toLong())
                        } catch (e: NumberFormatException) {
                            LogUtils.w("Firebase Performance: Invalid Content-Length header: $contentLength")
                        }
                    }

                    // 设置请求大小（如果可用）
                    val requestBody = response.request.body
                    if (requestBody != null) {
                        try {
                            httpMetric.setRequestPayloadSize(requestBody.contentLength())
                        } catch (e: Exception) {
                            // 忽略无法获取请求体大小的情况
                        }
                    }

                    // 设置响应属性
                    try {
                        // 设置响应状态
                        httpMetric.putAttribute("response_status", response.code.toString())

                        // 设置响应类型
                        val contentType = response.header("Content-Type")
                        if (!contentType.isNullOrEmpty()) {
                            httpMetric.putAttribute("content_type", contentType)
                        }

                        // 设置是否成功
                        httpMetric.putAttribute("success", (response.code in 200..299).toString())

                        // 设置响应时间（如果有的话）
                        val responseTime = response.header("X-Response-Time")
                        if (!responseTime.isNullOrEmpty()) {
                            httpMetric.putAttribute("server_response_time", responseTime)
                        }
                    } catch (e: Exception) {
                        LogUtils.w("Firebase Performance: Failed to set response attributes: ${e.message}")
                    }
                } else {
                    // 请求失败时设置错误响应码
                    httpMetric.setHttpResponseCode(0)
                    httpMetric.putAttribute("response_status", "0")
                    httpMetric.putAttribute("success", "false")
                    httpMetric.putAttribute("error", "network_failure")
                }

                httpMetric.stop()
            }
        } catch (e: Exception) {
            LogUtils.e("Firebase Performance: Failed to stop HTTP metric: ${e.message}")
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
