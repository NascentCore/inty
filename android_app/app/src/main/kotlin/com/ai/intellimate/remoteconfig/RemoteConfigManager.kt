package com.ai.intellimate.remoteconfig

import com.google.firebase.ktx.Firebase
import com.google.firebase.remoteconfig.FirebaseRemoteConfig
import com.google.firebase.remoteconfig.ktx.remoteConfig
import com.google.firebase.remoteconfig.ktx.remoteConfigSettings
import kotlinx.coroutines.tasks.await

/**
 * Firebase Remote Config 管理类
 * 用于统一管理应用的远程配置和 AB 测试
 */
object RemoteConfigManager {
    
    private lateinit var remoteConfig: FirebaseRemoteConfig
    
    // AB 测试配置键
    object ConfigKeys {
        const val BUTTON_COLOR = "button_color"
        const val BUTTON_TEXT = "button_text"
        const val FEATURE_ENABLED = "feature_enabled"
        const val WELCOME_MESSAGE = "welcome_message"
    }
    
    // 默认配置值
    private val defaultConfig = mapOf(
        ConfigKeys.BUTTON_COLOR to "#FF6200EE",
        ConfigKeys.BUTTON_TEXT to "点击我",
        ConfigKeys.FEATURE_ENABLED to false,
        ConfigKeys.WELCOME_MESSAGE to "欢迎使用我们的应用！"
    )
    
    /**
     * 初始化 Remote Config
     * @param fetchIntervalSeconds 获取间隔（秒），开发环境建议设为 0，生产环境建议 3600
     */
    fun initialize(fetchIntervalSeconds: Long = 0) {
        remoteConfig = Firebase.remoteConfig
        
        // 配置设置
        val configSettings = remoteConfigSettings {
            minimumFetchIntervalInSeconds = fetchIntervalSeconds
        }
        
        remoteConfig.setConfigSettingsAsync(configSettings)
        remoteConfig.setDefaultsAsync(defaultConfig)
    }
    
    /**
     * 获取并激活远程配置
     * @return 是否成功获取新配置
     */
    suspend fun fetchAndActivate(): Boolean {
        return try {
            remoteConfig.fetchAndActivate().await()
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }
    
    /**
     * 获取字符串配置
     */
    fun getString(key: String): String {
        return remoteConfig.getString(key)
    }
    
    /**
     * 获取布尔配置
     */
    fun getBoolean(key: String): Boolean {
        return remoteConfig.getBoolean(key)
    }
    
    /**
     * 获取长整型配置
     */
    fun getLong(key: String): Long {
        return remoteConfig.getLong(key)
    }
    
    /**
     * 获取双精度浮点配置
     */
    fun getDouble(key: String): Double {
        return remoteConfig.getDouble(key)
    }
    
    /**
     * 获取所有配置值（用于调试）
     */
    fun getAllConfigs(): Map<String, String> {
        return remoteConfig.all.mapValues { it.value.asString() }
    }
}
