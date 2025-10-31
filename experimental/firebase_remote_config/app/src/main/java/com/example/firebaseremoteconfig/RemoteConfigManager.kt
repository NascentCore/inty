package com.example.firebaseremoteconfig

import android.util.Log
import com.google.firebase.ktx.Firebase
import com.google.firebase.remoteconfig.FirebaseRemoteConfig
import com.google.firebase.remoteconfig.ktx.remoteConfig
import com.google.firebase.remoteconfig.ktx.remoteConfigSettings
import kotlinx.coroutines.tasks.await

/**
 * Firebase Remote Config 管理器
 * 用于获取和缓存远程配置，支持 AB 测试
 */
class RemoteConfigManager private constructor() {
    
    private val remoteConfig: FirebaseRemoteConfig = Firebase.remoteConfig
    
    companion object {
        private const val TAG = "RemoteConfigManager"
        
        // Remote Config 参数键名
        const val KEY_BUTTON_COLOR_VARIANT = "button_color_variant"
        const val KEY_WELCOME_MESSAGE = "welcome_message"
        const val KEY_ENABLE_NEW_FEATURE = "enable_new_feature"
        
        // 默认值
        private const val DEFAULT_BUTTON_VARIANT = "control"
        private const val DEFAULT_WELCOME_MESSAGE = "欢迎使用应用！"
        private const val DEFAULT_ENABLE_NEW_FEATURE = false
        
        @Volatile
        private var INSTANCE: RemoteConfigManager? = null
        
        fun getInstance(): RemoteConfigManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: RemoteConfigManager().also { INSTANCE = it }
            }
        }
    }
    
    init {
        // 配置 Remote Config 设置
        val configSettings = remoteConfigSettings {
            minimumFetchIntervalInSeconds = 3600 // 生产环境：1小时
            // 开发环境可以使用更短的间隔：
            // minimumFetchIntervalInSeconds = 0 // 每次调用都获取最新配置
        }
        remoteConfig.setConfigSettingsAsync(configSettings)
        
        // 设置默认值
        val defaultValues = mapOf(
            KEY_BUTTON_COLOR_VARIANT to DEFAULT_BUTTON_VARIANT,
            KEY_WELCOME_MESSAGE to DEFAULT_WELCOME_MESSAGE,
            KEY_ENABLE_NEW_FEATURE to DEFAULT_ENABLE_NEW_FEATURE
        )
        remoteConfig.setDefaultsAsync(defaultValues)
        
        // 注意：不在 init 中调用 fetchAndActivate()，因为它是 suspend 函数
        // 首次配置获取应在 ViewModel 的 loadConfig() 中进行
    }
    
    /**
     * 获取并激活远程配置
     * @return 是否成功获取新配置
     */
    suspend fun fetchAndActivate(): Boolean {
        return try {
            val result = remoteConfig.fetchAndActivate().await()
            Log.d(TAG, "Config fetched and activated: $result")
            result
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching config", e)
            false
        }
    }
    
    /**
     * 获取按钮颜色变体（AB 测试）
     * 可能的返回值: "control", "variant_a", "variant_b"
     */
    fun getButtonColorVariant(): String {
        return remoteConfig.getString(KEY_BUTTON_COLOR_VARIANT)
    }
    
    /**
     * 获取欢迎消息
     */
    fun getWelcomeMessage(): String {
        return remoteConfig.getString(KEY_WELCOME_MESSAGE)
    }
    
    /**
     * 检查是否启用新功能
     */
    fun isNewFeatureEnabled(): Boolean {
        return remoteConfig.getBoolean(KEY_ENABLE_NEW_FEATURE)
    }
    
    /**
     * 获取配置的最后更新时间戳
     */
    fun getLastFetchTime(): Long {
        return remoteConfig.info.fetchTimeMillis
    }
    
    /**
     * 获取配置状态信息
     */
    fun getConfigInfo(): String {
        val info = remoteConfig.info
        return buildString {
            append("最后获取时间: ${info.fetchTimeMillis}\n")
            append("上次状态: ${info.lastFetchStatus}\n")
            append("配置来源: ${info.configSettings}")
        }
    }
}
