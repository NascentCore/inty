package ai.sxwl.android.common.analytics

import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import android.app.Activity
import androidx.fragment.app.Fragment
import java.util.concurrent.ConcurrentHashMap

/**
 * 页面追踪工具类
 * 用于记录用户页面访问、交互流程和崩溃时的上下文信息
 * 提供业务层友好的页面追踪功能
 */
object PageTrackingHelper {

    // 当前页面信息
    private var currentPage: String? = null
    private var currentPageClass: String? = null
    private var pageStartTime: Long = 0L

    // 用户交互历史（最近10个操作）
    private val userInteractionHistory = ConcurrentHashMap<String, String>()
    private val maxHistorySize = 10

    // 页面访问历史
    private val pageHistory = mutableListOf<String>()
    private val maxPageHistorySize = 5

    /**
     * 记录页面访问
     */
    fun trackPageView(
        pageName: String,
        pageClass: String = "Unknown",
        additionalParams: Map<String, Any> = emptyMap(),
    ) {
        try {
            // 记录页面结束时间（如果有上一个页面）
            if (currentPage != null) {
                val timeSpent = System.currentTimeMillis() - pageStartTime
                LogUtils.i("Page tracking: $currentPage spent ${timeSpent}ms")
            }

            // 更新当前页面信息
            currentPage = pageName
            currentPageClass = pageClass
            pageStartTime = System.currentTimeMillis()

            // 添加到页面历史
            addToPageHistory(pageName)

            // 设置 Crashlytics 自定义键
            FirebaseManager.setCustomKey("current_page", pageName)
            FirebaseManager.setCustomKey("current_page_class", pageClass)
            FirebaseManager.setCustomKey("page_start_time", pageStartTime.toString())

            // 记录 Analytics 事件
            FirebaseManager.logScreenView(
                pageName,
                pageClass,
                additionalParams + mapOf("timestamp" to System.currentTimeMillis()),
            )
        } catch (e: Exception) {
            LogUtils.e("Failed to track page view: ${e.message}")
        }
    }

    /**
     * 记录用户交互
     */
    fun trackUserInteraction(
        action: String,
        target: String,
        additionalParams: Map<String, Any> = emptyMap(),
    ) {
        try {
            val timestamp = System.currentTimeMillis()
            val interactionKey = "${action}_${target}_${timestamp}"

            // 添加到交互历史
            addToInteractionHistory(interactionKey, "$action on $target")

            // 设置 Crashlytics 自定义键
            FirebaseManager.setCustomKey("last_interaction", "$action on $target")
            FirebaseManager.setCustomKey("last_interaction_time", timestamp.toString())

            // 记录 Analytics 事件
            FirebaseManager.logEvent(
                "user_interaction",
                mapOf(
                    "action" to action,
                    "target" to target,
                    "current_page" to (currentPage ?: "unknown"),
                    "timestamp" to timestamp,
                ) + additionalParams,
            )

        } catch (e: Exception) {
            LogUtils.e("Failed to track user interaction: ${e.message}")
        }
    }

    /**
     * 记录按钮点击
     */
    fun trackButtonClick(
        buttonName: String,
        pageName: String? = currentPage,
        additionalParams: Map<String, Any> = emptyMap(),
    ) {
        trackUserInteraction(
            "click",
            buttonName,
            additionalParams + mapOf("page" to (pageName ?: "unknown")),
        )
    }

    /**
     * 记录网络请求
     */
    fun trackNetworkRequest(
        url: String,
        method: String,
        success: Boolean,
        responseTime: Long = 0L,
    ) {
        try {
            FirebaseManager.logEvent(
                "network_request",
                mapOf(
                    "url" to url,
                    "method" to method,
                    "success" to success,
                    "response_time" to responseTime,
                    "current_page" to (currentPage ?: "unknown"),
                ),
            )

            // 设置 Crashlytics 自定义键
            FirebaseManager.setCustomKey("last_network_request", "$method $url")
            FirebaseManager.setCustomKey("last_network_success", success.toString())

        } catch (e: Exception) {
            LogUtils.e("Failed to track network request: ${e.message}")
        }
    }

    /**
     * 记录错误和异常
     */
    fun trackError(
        error: String,
        errorType: String = "unknown",
        additionalParams: Map<String, Any> = emptyMap(),
    ) {
        try {
            FirebaseManager.logEvent(
                "app_error",
                mapOf(
                    "error" to error,
                    "error_type" to errorType,
                    "current_page" to (currentPage ?: "unknown"),
                    "page_class" to (currentPageClass ?: "unknown"),
                    "timestamp" to System.currentTimeMillis(),
                ) + additionalParams,
            )

            // 设置 Crashlytics 自定义键
            FirebaseManager.setCustomKey("last_error", error)
            FirebaseManager.setCustomKey("last_error_type", errorType)
            FirebaseManager.setCustomKey("error_page", currentPage ?: "unknown")

        } catch (e: Exception) {
            LogUtils.e("Failed to track error: ${e.message}")
        }
    }

    /**
     * 获取当前页面信息
     */
    fun getCurrentPageInfo(): Map<String, Any> {
        return mapOf(
            "current_page" to (currentPage ?: "unknown"),
            "current_page_class" to (currentPageClass ?: "unknown"),
            "page_start_time" to pageStartTime,
            "time_on_page" to (System.currentTimeMillis() - pageStartTime),
            "interaction_history" to userInteractionHistory.toMap(),
            "page_history" to pageHistory.toList(),
        )
    }

    /**
     * 设置用户标识
     */
    fun setUserId(userId: String) {
        try {
            FirebaseManager.setUserId(userId)
            FirebaseManager.setCustomKey("user_id", userId)
        } catch (e: Exception) {
            LogUtils.e("Failed to set user ID: ${e.message}")
        }
    }

    /**
     * 设置用户属性
     */
    fun setUserProperty(property: String, value: String) {
        try {
            FirebaseManager.setUserProperty(property, value)
            FirebaseManager.setCustomKey("user_$property", value)
        } catch (e: Exception) {
            LogUtils.e("Failed to set user property: ${e.message}")
        }
    }

    private fun addToInteractionHistory(key: String, value: String) {
        userInteractionHistory[key] = value
        if (userInteractionHistory.size > maxHistorySize) {
            val oldestKey = userInteractionHistory.keys.first()
            userInteractionHistory.remove(oldestKey)
        }
    }

    private fun addToPageHistory(pageName: String) {
        pageHistory.add(pageName)
        if (pageHistory.size > maxPageHistorySize) {
            pageHistory.removeAt(0)
        }
    }

    /**
     * 为 Activity 添加生命周期追踪
     */
    fun trackActivityLifecycle(activity: Activity, pageName: String) {
        trackPageView(pageName, activity.javaClass.simpleName)
    }

    /**
     * 为 Fragment 添加生命周期追踪
     */
    fun trackFragmentLifecycle(fragment: Fragment, pageName: String) {
        trackPageView(pageName, fragment.javaClass.simpleName)
    }
}
