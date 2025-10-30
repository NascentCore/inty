package ai.sxwl.android.firebase

import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import android.content.Context
import com.google.firebase.remoteconfig.FirebaseRemoteConfig
import com.google.firebase.remoteconfig.FirebaseRemoteConfigSettings

/**
 * RemoteConfig 管理器
 * - 负责 Remote Config 的初始化、默认值设置、fetch/activate
 * - 提供类型安全的获取接口与关键参数常量
 */
object RemoteConfigManager {

    // ===== Remote Config 参数键（面向业务暴露）=====
    const val KEY_PROFILE_AVATAR_MAX_SIZE_MB = "profile_avatar_max_size_mb"
    const val KEY_AB_PROFILE_AVATAR_MESSAGE_VARIANT = "ab_profile_avatar_message_variant" // "A" | "B"

    @Volatile
    private var isInitialized: Boolean = false

    private val remoteConfig: FirebaseRemoteConfig by lazy { FirebaseRemoteConfig.getInstance() }

    /** 初始化 Remote Config（幂等） */
    fun initialize(context: Context) {
        if (isInitialized) return
        runCatching {
            val minFetchSeconds = if (AppUtils.isAppDebug()) 0L else 3600L
            val settings =
                FirebaseRemoteConfigSettings.Builder()
                    .setMinimumFetchIntervalInSeconds(minFetchSeconds)
                    .build()
            remoteConfig.setConfigSettingsAsync(settings)

            // 设置默认值，保证未联网/首次启动也有合理的行为
            val defaults = mapOf(
                KEY_PROFILE_AVATAR_MAX_SIZE_MB to 10L, // 默认 10MB
                KEY_AB_PROFILE_AVATAR_MESSAGE_VARIANT to "A", // 默认变体 A
            )
            remoteConfig.setDefaultsAsync(defaults)

            isInitialized = true
            // 异步拉取最新配置
            fetchAndActivate()
        }.onFailure { e ->
            LogUtils.e("RemoteConfigManager", "初始化失败: ${e.message}")
        }
    }

    /** 拉取并激活配置（安全封装） */
    fun fetchAndActivate(onComplete: ((Boolean) -> Unit)? = null) {
        if (!isInitialized) {
            onComplete?.invoke(false)
            return
        }
        remoteConfig.fetchAndActivate().addOnCompleteListener { task ->
            val ok = task.isSuccessful
            if (AppUtils.isAppDebug()) {
                LogUtils.d("RemoteConfigManager", "fetchAndActivate success=$ok")
            }
            onComplete?.invoke(ok)
        }
    }

    fun getLong(key: String, defaultValue: Long): Long {
        if (!isInitialized) return defaultValue
        return runCatching { remoteConfig.getLong(key) }.getOrDefault(defaultValue)
    }

    fun getString(key: String, defaultValue: String): String {
        if (!isInitialized) return defaultValue
        return runCatching { remoteConfig.getString(key) }.getOrDefault(defaultValue)
    }

    fun getBoolean(key: String, defaultValue: Boolean): Boolean {
        if (!isInitialized) return defaultValue
        return runCatching { remoteConfig.getBoolean(key) }.getOrDefault(defaultValue)
    }

    fun getDouble(key: String, defaultValue: Double): Double {
        if (!isInitialized) return defaultValue
        return runCatching { remoteConfig.getDouble(key) }.getOrDefault(defaultValue)
    }
}
