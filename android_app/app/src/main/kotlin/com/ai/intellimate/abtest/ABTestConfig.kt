package com.ai.intellimate.abtest

import com.google.firebase.remoteconfig.FirebaseRemoteConfig
import com.google.firebase.remoteconfig.FirebaseRemoteConfigSettings
import kotlinx.coroutines.tasks.await
import javax.inject.Inject
import javax.inject.Singleton

/**
 * AB 测试配置管理类
 * 使用 Firebase Remote Config 进行远程配置管理
 */
@Singleton
class ABTestConfig @Inject constructor() {
    
    private val remoteConfig: FirebaseRemoteConfig = FirebaseRemoteConfig.getInstance()
    
    init {
        // 配置 Remote Config 设置
        val configSettings = FirebaseRemoteConfigSettings.Builder()
            .setMinimumFetchIntervalInSeconds(3600) // 1小时缓存
            .build()
        remoteConfig.setConfigSettingsAsync(configSettings)
        
        // 设置默认值
        setDefaultValues()
    }
    
    /**
     * 设置默认配置值
     */
    private fun setDefaultValues() {
        val defaults = mapOf(
            "welcome_button_color" to "blue",
            "welcome_button_text" to "开始体验",
            "show_premium_banner" to true,
            "chat_ui_style" to "modern",
            "feature_flag_new_ui" to false
        )
        remoteConfig.setDefaultsAsync(defaults)
    }
    
    /**
     * 获取远程配置
     */
    suspend fun fetchAndActivate(): Boolean {
        return try {
            remoteConfig.fetchAndActivate().await()
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * 获取欢迎按钮颜色
     */
    fun getWelcomeButtonColor(): String {
        return remoteConfig.getString("welcome_button_color")
    }
    
    /**
     * 获取欢迎按钮文本
     */
    fun getWelcomeButtonText(): String {
        return remoteConfig.getString("welcome_button_text")
    }
    
    /**
     * 是否显示高级功能横幅
     */
    fun shouldShowPremiumBanner(): Boolean {
        return remoteConfig.getBoolean("show_premium_banner")
    }
    
    /**
     * 获取聊天界面样式
     */
    fun getChatUIStyle(): String {
        return remoteConfig.getString("chat_ui_style")
    }
    
    /**
     * 是否启用新 UI 功能
     */
    fun isNewUIFeatureEnabled(): Boolean {
        return remoteConfig.getBoolean("feature_flag_new_ui")
    }
    
    /**
     * 获取所有配置信息（用于调试）
     */
    fun getAllConfigs(): Map<String, Any> {
        return mapOf(
            "welcome_button_color" to getWelcomeButtonColor(),
            "welcome_button_text" to getWelcomeButtonText(),
            "show_premium_banner" to shouldShowPremiumBanner(),
            "chat_ui_style" to getChatUIStyle(),
            "feature_flag_new_ui" to isNewUIFeatureEnabled()
        )
    }
}