package ai.sxwl.android.firebase

import android.content.Context
import com.google.firebase.Firebase
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.analytics.analytics
import com.google.firebase.analytics.logEvent
import com.google.firebase.crashlytics.FirebaseCrashlytics
import com.google.firebase.crashlytics.crashlytics
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

/**
 * Firebase管理器
 * 负责Firebase Analytics和Crashlytics的初始化和使用
 */
object FirebaseManager {

    private lateinit var analytics: FirebaseAnalytics
    private lateinit var crashlytics: FirebaseCrashlytics

    /**
     * 初始化Firebase服务
     */
    fun initialize(context: Context) {
        analytics = Firebase.analytics
        crashlytics = Firebase.crashlytics

        // 设置Crashlytics用户标识（可选）
        // crashlytics.setUserId("user_id")

        // 设置自定义键值对（可选）
        // crashlytics.setCustomKey("app_version", BuildConfig.VERSION_NAME)
    }

    /**
     * 记录自定义事件
     */
    fun logEvent(eventName: String, parameters: Map<String, Any>? = null) {
        analytics.logEvent(eventName) {
            parameters?.forEach { (key, value) ->
                when (value) {
                    is String -> param(key, value)
                    is Long -> param(key, value)
                    is Int -> param(key, value.toLong())
                    is Double -> param(key, value)
                    is Boolean -> param(key, value.toString())
                }
            }
        }
    }

    /**
     * 记录用户属性
     */
    fun setUserProperty(name: String, value: String) {
        analytics.setUserProperty(name, value)
    }

    /**
     * 记录用户ID
     */
    fun setUserId(userId: String) {
        analytics.setUserId(userId)
        crashlytics.setUserId(userId)
    }

    /**
     * 记录非致命错误
     */
    fun recordException(throwable: Throwable) {
        crashlytics.recordException(throwable)
    }

    /**
     * 记录自定义日志
     */
    fun log(message: String) {
        crashlytics.log(message)
    }

    /**
     * 设置自定义键值对到Crashlytics
     */
    fun setCustomKey(key: String, value: String) {
        crashlytics.setCustomKey(key, value)
    }

    fun setCustomKey(key: String, value: Boolean) {
        crashlytics.setCustomKey(key, value)
    }

    fun setCustomKey(key: String, value: Int) {
        crashlytics.setCustomKey(key, value)
    }

    fun setCustomKey(key: String, value: Long) {
        crashlytics.setCustomKey(key, value)
    }

    fun setCustomKey(key: String, value: Float) {
        crashlytics.setCustomKey(key, value)
    }

    fun setCustomKey(key: String, value: Double) {
        crashlytics.setCustomKey(key, value)
    }

    /**
     * 异步记录事件（避免阻塞主线程）
     */
    fun logEventAsync(eventName: String, parameters: Map<String, Any>? = null) {
        CoroutineScope(Dispatchers.IO).launch {
            logEvent(eventName, parameters)
        }
    }

    /**
     * 预定义的事件常量
     */
    object Events {
        const val APP_OPEN = "app_open"
        const val USER_LOGIN = "user_login"
        const val USER_LOGOUT = "user_logout"
        const val CHAT_STARTED = "chat_started"
        const val MESSAGE_SENT = "message_sent"
        const val AI_RESPONSE_RECEIVED = "ai_response_received"
        const val PROFILE_UPDATED = "profile_updated"
        const val SETTINGS_CHANGED = "settings_changed"
    }

    /**
     * 预定义的用户属性常量
     */
    object UserProperties {
        const val USER_TYPE = "user_type"
        const val SUBSCRIPTION_LEVEL = "subscription_level"
        const val APP_VERSION = "app_version"
        const val DEVICE_TYPE = "device_type"
    }


    //firebase 推送消息注册

    suspend fun registerFCM(): String {
        val token = FirebaseMessaging.getInstance().token.await()
        return token
    }
}
