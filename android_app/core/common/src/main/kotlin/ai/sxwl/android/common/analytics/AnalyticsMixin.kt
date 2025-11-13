package ai.sxwl.android.common.analytics

import ai.sxwl.android.firebase.FirebaseManager

/**
 * Analytics功能混入接口 提供统一的Analytics功能，可以被任何需要Analytics能力的类实现
 *
 * 设计原则：
 * - 单一职责：只负责Analytics功能
 * - 开闭原则：易于扩展新的Analytics功能
 * - 接口隔离：提供细粒度的Analytics接口
 */
interface AnalyticsMixin {

    /** 页面名称，实现类需要提供 */
    val screenName: String

    /** 页面类名，实现类需要提供 */
    val screenClass: String

    /** 额外的页面参数，实现类可以重写 */
    val additionalParams: Map<String, Any>
        get() = emptyMap()

    /** 是否已经跟踪过页面访问 */
    var hasTrackedScreenView: Boolean

    /** 跟踪页面访问 通常在ViewModel初始化时调用 */
    fun trackScreenView() {
        if (!hasTrackedScreenView) {
            FirebaseManager.logScreenView(
                screenName = screenName,
                screenClass = screenClass,
                additionalParams = additionalParams,
            )
            // 使用PageTrackingHelper进行更详细的页面追踪
            PageTrackingHelper.trackPageView(screenName, screenClass, additionalParams)
            hasTrackedScreenView = true
        }
    }

    /** 跟踪用户行为事件 */
    fun trackEvent(eventName: String, params: Map<String, Any> = emptyMap()) {
        FirebaseManager.logEvent(eventName, params)
    }

    /** 跟踪页面内的特定操作 */
    fun trackPageAction(action: String, params: Map<String, Any> = emptyMap()) {
        val eventName = "${screenName}_$action"
        val allParams = params + mapOf("screen_name" to screenName, "screen_class" to screenClass)
        trackEvent(eventName, allParams)
    }

    /** 跟踪错误事件 */
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

    /** 跟踪用户操作 */
    fun trackUserAction(
        action: String,
        target: String? = null,
        params: Map<String, Any> = emptyMap(),
    ) {
        val actionParams =
            params +
                mapOf(
                    "action" to action,
                    "screen_name" to screenName,
                    "screen_class" to screenClass,
                ) +
                (target?.let { mapOf("target" to it) } ?: emptyMap())

        trackEvent("user_action", actionParams)
    }

    /** 跟踪业务事件 */
    fun trackBusinessEvent(businessEvent: String, params: Map<String, Any> = emptyMap()) {
        val businessParams =
            params +
                mapOf(
                    "business_event" to businessEvent,
                    "screen_name" to screenName,
                    "screen_class" to screenClass,
                )
        trackEvent("business_event", businessParams)
    }

    /** 跟踪按钮点击（使用PageTrackingHelper） */
    fun trackButtonClick(buttonName: String, params: Map<String, Any> = emptyMap()) {
        PageTrackingHelper.trackButtonClick(buttonName, screenName, params)
    }

    /** 跟踪网络请求（使用PageTrackingHelper） */
    fun trackNetworkRequest(
        url: String,
        method: String,
        success: Boolean,
        responseTime: Long = 0L,
    ) {
        PageTrackingHelper.trackNetworkRequest(url, method, success, responseTime)
    }

    /** 跟踪应用错误（使用PageTrackingHelper） */
    fun trackAppError(
        error: String,
        errorType: String = "unknown",
        params: Map<String, Any> = emptyMap(),
    ) {
        PageTrackingHelper.trackError(error, errorType, params)
    }

    /** 获取当前页面信息 */
    fun getCurrentPageInfo(): Map<String, Any> {
        return PageTrackingHelper.getCurrentPageInfo()
    }
}
