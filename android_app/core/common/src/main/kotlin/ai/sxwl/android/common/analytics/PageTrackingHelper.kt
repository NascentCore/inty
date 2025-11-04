package ai.sxwl.android.common.analytics

import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import androidx.activity.ComponentActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.LifecycleOwner
import java.util.concurrent.ConcurrentHashMap

/** 页面追踪工具类 用于记录用户页面访问、交互流程和崩溃时的上下文信息 提供业务层友好的页面追踪功能 */
object PageTrackingHelper {

    /** 用户交互操作常量 - 用于性能追踪和用户行为分析
     * 注意：这些是用户操作的 action 类型，不是 Firebase 事件名称
     * 应该使用通用的操作动词，便于性能分析和用户行为统计
     */
    object UserActions {
        // 基础交互操作
        const val CLICK = "click" // 点击操作
        const val TAP = "tap" // 轻触操作（移动端）
        const val SWIPE = "swipe" // 滑动操作
        const val LONG_PRESS = "long_press" // 长按操作

        // 消息相关操作
        const val SEND_MESSAGE = "send_message" // 发送消息（用户操作类型）
        const val INPUT_TEXT = "input_text" // 输入文本

        // 会话相关操作
        const val START_SESSION = "start_session" // 开始会话（用户操作类型）
        const val END_SESSION = "end_session" // 结束会话
        const val SWITCH_AGENT = "switch_agent" // 切换Agent

        // 媒体操作
        const val PLAY_AUDIO = "play_audio" // 播放音频
        const val PAUSE_AUDIO = "pause_audio" // 暂停音频
        const val STOP_AUDIO = "stop_audio" // 停止音频

        // UI操作
        const val OPEN = "open" // 打开
        const val CLOSE = "close" // 关闭
        const val SHOW = "show" // 显示
        const val HIDE = "hide" // 隐藏
    }

    // 当前页面信息
    private var currentPage: String? = null
    private var currentPageClass: String? = null
    private var pageStartTime: Long = 0L
    private var pageVisibleTime: Long = 0L // 页面可见开始时间
    private var pageLifecycleStartTime: Long = 0L // 页面生命周期开始时间

    // 用户交互历史（最近10个操作）
    private val userInteractionHistory = ConcurrentHashMap<String, String>()
    private val maxHistorySize = 10

    // 页面访问历史
    private val pageHistory = mutableListOf<String>()
    private val maxPageHistorySize = 5

    /** 记录页面访问 */
    fun trackPageView(
        pageName: String,
        pageClass: String = "Unknown",
        additionalParams: Map<String, Any> = emptyMap(),
    ) {
        try {
            val currentTime = System.currentTimeMillis()

            // 记录上一个页面的停留时长（如果有）
            if (currentPage != null) {
                val timeSpent = currentTime - pageStartTime
                val visibleTimeSpent =
                    if (pageVisibleTime > 0) currentTime - pageVisibleTime else 0L
                val lifecycleTimeSpent =
                    if (pageLifecycleStartTime > 0) currentTime - pageLifecycleStartTime else 0L

                LogUtils.i(
                    "页面访问追踪: $currentPage 停留时长=${timeSpent}ms, 可见时长=${visibleTimeSpent}ms, 生命周期时长=${lifecycleTimeSpent}ms"
                )

                // 记录页面离开事件
                FirebaseManager.logEvent(
                    "page_leave",
                    FirebaseManager.safeEventParams(
                        "page_name" to currentPage,
                        "page_class" to (currentPageClass ?: "unknown"),
                        "time_spent" to timeSpent,
                        "visible_time_spent" to visibleTimeSpent,
                        "lifecycle_time_spent" to lifecycleTimeSpent,
                        "timestamp" to currentTime
                    )
                )
            }

            // 更新当前页面信息
            currentPage = pageName
            currentPageClass = pageClass
            pageStartTime = currentTime
            pageVisibleTime = currentTime // 假设页面访问时就是可见的
            pageLifecycleStartTime = currentTime

            // 添加到页面历史
            addToPageHistory(pageName)

            // 设置 Crashlytics 自定义键
            FirebaseManager.setCustomKey("current_page", pageName)
            FirebaseManager.setCustomKey("current_page_class", pageClass)
            FirebaseManager.setCustomKey("page_start_time", pageStartTime.toString())
            FirebaseManager.setCustomKey("page_visible_time", pageVisibleTime.toString())
            FirebaseManager.setCustomKey(
                "page_lifecycle_start_time",
                pageLifecycleStartTime.toString()
            )

            // 记录 Analytics 事件 - 使用安全参数处理
            val safeParams =
                FirebaseManager.safeEventParams(
                    "timestamp" to currentTime,
                    "page_name" to pageName,
                    "page_class" to pageClass
                ) + additionalParams.mapValues { it.value?.toString() ?: "unknown" }

            FirebaseManager.logScreenView(pageName, pageClass, safeParams)
        } catch (e: Exception) {
            LogUtils.e("Failed to track page view: ${e.message}")
        }
    }

    /** 记录页面可见性变化 */
    fun trackPageVisibility(isVisible: Boolean) {
        try {
            val currentTime = System.currentTimeMillis()

            if (isVisible) {
                // 页面变为可见
                pageVisibleTime = currentTime
                LogUtils.i("页面可见性追踪: $currentPage 变为可见")

                FirebaseManager.logEvent(
                    "page_visible",
                    FirebaseManager.safeEventParams(
                        "page_name" to (currentPage ?: "unknown"),
                        "page_class" to (currentPageClass ?: "unknown"),
                        "timestamp" to currentTime
                    )
                )
            } else {
                // 页面变为不可见
                if (pageVisibleTime > 0) {
                    val visibleTimeSpent = currentTime - pageVisibleTime
                    LogUtils.i("页面可见性追踪: $currentPage 变为不可见，可见时长=${visibleTimeSpent}ms")

                    FirebaseManager.logEvent(
                        "page_hidden",
                        FirebaseManager.safeEventParams(
                            "page_name" to (currentPage ?: "unknown"),
                            "page_class" to (currentPageClass ?: "unknown"),
                            "visible_time_spent" to visibleTimeSpent,
                            "timestamp" to currentTime
                        )
                    )
                }
                pageVisibleTime = 0L // 重置可见时间
            }
        } catch (e: Exception) {
            LogUtils.e("Failed to track page visibility: ${e.message}")
        }
    }

    /** 记录页面生命周期变化 */
    fun trackPageLifecycle(lifecycleEvent: String) {
        try {
            val currentTime = System.currentTimeMillis()

            when (lifecycleEvent.lowercase()) {
                "oncreate",
                "onstart" -> {
                    if (pageLifecycleStartTime == 0L) {
                        pageLifecycleStartTime = currentTime
                    }
                }

                "ondestroy",
                "onstop" -> {
                    if (pageLifecycleStartTime > 0) {
                        val lifecycleTimeSpent = currentTime - pageLifecycleStartTime
                        LogUtils.i(
                            "页面生命周期追踪: $currentPage $lifecycleEvent，生命周期时长=${lifecycleTimeSpent}ms"
                        )

                        FirebaseManager.logEvent(
                            "page_lifecycle",
                            FirebaseManager.safeEventParams(
                                "page_name" to (currentPage ?: "unknown"),
                                "page_class" to (currentPageClass ?: "unknown"),
                                "lifecycle_event" to lifecycleEvent,
                                "lifecycle_time_spent" to lifecycleTimeSpent,
                                "timestamp" to currentTime
                            )
                        )

                        // 重置生命周期开始时间
                        pageLifecycleStartTime = 0L
                    }
                }
            }
        } catch (e: Exception) {
            LogUtils.e("Failed to track page lifecycle: ${e.message}")
        }
    }

    /** 记录用户交互 */
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

    /** 记录按钮点击 */
    fun trackButtonClick(
        buttonName: String,
        pageName: String? = currentPage,
        additionalParams: Map<String, Any> = emptyMap(),
    ) {
        trackUserInteraction(
            UserActions.CLICK,
            buttonName,
            additionalParams + mapOf("page" to (pageName ?: "unknown")),
        )
    }

    /** 记录网络请求 */
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

    /** 记录错误和异常 */
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

    /** 获取当前页面信息 */
    fun getCurrentPageInfo(): Map<String, Any> {
        val currentTime = System.currentTimeMillis()
        return mapOf(
            "current_page" to (currentPage ?: "unknown"),
            "current_page_class" to (currentPageClass ?: "unknown"),
            "page_start_time" to pageStartTime,
            "page_visible_time" to pageVisibleTime,
            "page_lifecycle_start_time" to pageLifecycleStartTime,
            "time_on_page" to (currentTime - pageStartTime),
            "visible_time_on_page" to
                    if (pageVisibleTime > 0) (currentTime - pageVisibleTime) else 0L,
            "lifecycle_time_on_page" to
                    if (pageLifecycleStartTime > 0) (currentTime - pageLifecycleStartTime) else 0L,
            "interaction_history" to userInteractionHistory.toMap(),
            "page_history" to pageHistory.toList(),
        )
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

    /** 为 Activity 添加生命周期追踪 - 使用Lifecycle自动监听 */
    fun trackActivityLifecycle(activity: ComponentActivity, pageName: String) {
        // 记录页面访问
        trackPageView(pageName, activity.javaClass.simpleName)

        // 注册生命周期监听器
        registerLifecycleObserver(activity)
    }

    /** 为 Activity 注册生命周期监听器（不包含 trackPageView 调用） */
    fun trackActivityLifecycleWithoutPageView(activity: ComponentActivity) {
        // 只注册生命周期监听器，不调用 trackPageView
        registerLifecycleObserver(activity)
    }

    /** 注册生命周期监听器 */
    private fun registerLifecycleObserver(activity: ComponentActivity) {
        activity.lifecycle.addObserver(
            object : LifecycleEventObserver {
                override fun onStateChanged(source: LifecycleOwner, event: Lifecycle.Event) {
                    when (event) {
                        Lifecycle.Event.ON_CREATE -> trackPageLifecycle("onCreate")
                        Lifecycle.Event.ON_START -> trackPageLifecycle("onStart")
                        Lifecycle.Event.ON_RESUME -> {
                            trackPageVisibility(true)
                            trackPageLifecycle("onResume")
                        }

                        Lifecycle.Event.ON_PAUSE -> {
                            trackPageVisibility(false)
                            trackPageLifecycle("onPause")
                        }

                        Lifecycle.Event.ON_STOP -> trackPageLifecycle("onStop")
                        Lifecycle.Event.ON_DESTROY -> trackPageLifecycle("onDestroy")
                        Lifecycle.Event.ON_ANY -> {
                            // 不需要处理ON_ANY事件
                        }
                    }
                }
            }
        )

        LogUtils.i("PageTrackingHelper - 已为 ${activity.javaClass.simpleName} 注册生命周期追踪")
    }
}
