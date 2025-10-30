package com.ai.intellimate.abtest

import android.content.Context
import android.util.Log
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.analytics.ktx.analytics
import com.google.firebase.analytics.ktx.logEvent
import com.google.firebase.ktx.Firebase
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

/**
 * AB 测试管理器
 * 负责管理 AB 测试的初始化和事件追踪
 */
@Singleton
class ABTestManager @Inject constructor(
    private val abTestConfig: ABTestConfig
) {
    
    private val analytics: FirebaseAnalytics = Firebase.analytics
    private val coroutineScope = CoroutineScope(Dispatchers.IO)
    
    companion object {
        private const val TAG = "ABTestManager"
        
        // 事件名称
        const val EVENT_AB_TEST_INITIALIZED = "ab_test_initialized"
        const val EVENT_AB_TEST_CONFIG_LOADED = "ab_test_config_loaded"
        const val EVENT_BUTTON_CLICKED = "ab_test_button_clicked"
        const val EVENT_UI_STYLE_CHANGED = "ab_test_ui_style_changed"
        
        // 参数名称
        const val PARAM_BUTTON_COLOR = "button_color"
        const val PARAM_BUTTON_TEXT = "button_text"
        const val PARAM_UI_STYLE = "ui_style"
        const val PARAM_PREMIUM_BANNER_SHOWN = "premium_banner_shown"
        const val PARAM_NEW_UI_ENABLED = "new_ui_enabled"
    }
    
    /**
     * 初始化 AB 测试
     */
    fun initializeABTest() {
        coroutineScope.launch {
            try {
                // 获取远程配置
                val success = abTestConfig.fetchAndActivate()
                
                if (success) {
                    Log.d(TAG, "AB 测试配置加载成功")
                    logABTestInitialized()
                } else {
                    Log.w(TAG, "AB 测试配置加载失败，使用默认配置")
                }
            } catch (e: Exception) {
                Log.e(TAG, "AB 测试初始化失败", e)
            }
        }
    }
    
    /**
     * 记录 AB 测试初始化事件
     */
    private fun logABTestInitialized() {
        val configs = abTestConfig.getAllConfigs()
        
        analytics.logEvent(EVENT_AB_TEST_INITIALIZED) {
            param(PARAM_BUTTON_COLOR, configs["welcome_button_color"] as String)
            param(PARAM_BUTTON_TEXT, configs["welcome_button_text"] as String)
            param(PARAM_UI_STYLE, configs["chat_ui_style"] as String)
            param(PARAM_PREMIUM_BANNER_SHOWN, configs["show_premium_banner"] as Boolean)
            param(PARAM_NEW_UI_ENABLED, configs["feature_flag_new_ui"] as Boolean)
        }
    }
    
    /**
     * 记录按钮点击事件
     */
    fun logButtonClicked(buttonType: String) {
        analytics.logEvent(EVENT_BUTTON_CLICKED) {
            param("button_type", buttonType)
            param(PARAM_BUTTON_COLOR, abTestConfig.getWelcomeButtonColor())
            param(PARAM_BUTTON_TEXT, abTestConfig.getWelcomeButtonText())
        }
    }
    
    /**
     * 记录 UI 样式变更事件
     */
    fun logUIStyleChanged() {
        analytics.logEvent(EVENT_UI_STYLE_CHANGED) {
            param(PARAM_UI_STYLE, abTestConfig.getChatUIStyle())
            param(PARAM_NEW_UI_ENABLED, abTestConfig.isNewUIFeatureEnabled())
        }
    }
    
    /**
     * 获取当前 AB 测试配置
     */
    fun getCurrentConfig(): ABTestConfig = abTestConfig
}