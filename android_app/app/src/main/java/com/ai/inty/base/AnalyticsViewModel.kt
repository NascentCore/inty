package com.ai.inty.base

import androidx.lifecycle.ViewModel
import com.ai.inty.utils.FirebaseManager

/** 带有Analytics功能的ViewModel基类 提供统一的页面跟踪和事件跟踪功能 */
abstract class AnalyticsViewModel : ViewModel() {

    /** 页面名称，子类需要重写 */
    abstract val screenName: String

    /** 页面类名，子类需要重写 */
    abstract val screenClass: String

    /** 额外的页面参数，子类可以重写 */
    open val additionalParams: Map<String, Any> = emptyMap()

    /** 是否已经跟踪过页面访问 */
    private var hasTrackedScreenView = false

    /** 跟踪页面访问 通常在ViewModel初始化时调用 */
    fun trackScreenView() {
        if (!hasTrackedScreenView) {
            FirebaseManager.logScreenView(
                screenName = screenName,
                screenClass = screenClass,
                additionalParams = additionalParams,
            )
            hasTrackedScreenView = true
        }
    }

    /**
     * 跟踪用户行为事件
     *
     * @param eventName 事件名称
     * @param params 事件参数
     */
    fun trackEvent(eventName: String, params: Map<String, Any> = emptyMap()) {
        FirebaseManager.logEvent(eventName, params)
    }

    /**
     * 跟踪页面内的特定操作
     *
     * @param action 操作名称
     * @param params 操作参数
     */
    fun trackPageAction(action: String, params: Map<String, Any> = emptyMap()) {
        val eventName = "${screenName}_$action"
        val allParams = params + mapOf("screen_name" to screenName, "screen_class" to screenClass)
        trackEvent(eventName, allParams)
    }

    /**
     * 跟踪错误事件
     *
     * @param error 错误信息
     * @param params 额外参数
     */
    fun trackError(error: String, params: Map<String, Any> = emptyMap()) {
        val errorParams =
            params +
                mapOf(
                    "error_message" to error,
                    "screen_name" to screenName,
                    "screen_class" to screenClass,
                )
        trackEvent("error_occurred", errorParams)
    }

    /**
     * 跟踪性能指标
     *
     * @param metric 指标名称
     * @param value 指标值
     * @param unit 单位
     */
    fun trackPerformance(metric: String, value: Number, unit: String = "") {
        val params =
            mapOf(
                "metric_name" to metric,
                "metric_value" to value,
                "metric_unit" to unit,
                "screen_name" to screenName,
                "screen_class" to screenClass,
            )
        trackEvent("performance_metric", params)
    }
}
