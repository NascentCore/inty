package com.ai.inty.utils

import android.content.Context
import android.os.Bundle
import com.google.firebase.analytics.FirebaseAnalytics
import com.inty.utils.log.EasyLog

/**
 * Firebase Analytics 工具类
 * 用于跟踪Compose页面的screen view，解决Firebase只能看到Activity级别的问题
 */
object FirebaseAnalyticsHelper {
    
    private var firebaseAnalytics: FirebaseAnalytics? = null
    
    /**
     * 初始化FirebaseAnalytics实例
     * 应该在Application或Activity中调用
     */
    fun initialize(context: Context) {
        firebaseAnalytics = FirebaseAnalytics.getInstance(context)
        EasyLog.log("FirebaseAnalyticsHelper - 初始化完成")
    }
    
    /**
     * 跟踪Compose页面访问
     * @param screenName 页面名称，如 "ChatScreen", "HomeScreen", "ProfileScreen"
     * @param screenClass 页面类名，如 "ChatActivity", "MainActivity"
     * @param additionalParams 额外的参数，如用户ID、角色ID等
     */
    fun trackScreenView(
        screenName: String,
        screenClass: String,
        additionalParams: Map<String, Any> = emptyMap()
    ) {
        try {
            val analytics = firebaseAnalytics
            if (analytics == null) {
                EasyLog.log("FirebaseAnalyticsHelper - 未初始化，跳过页面跟踪", EasyLog.WARN)
                return
            }
            
            val bundle = Bundle().apply {
                putString(FirebaseAnalytics.Param.SCREEN_NAME, screenName)
                putString(FirebaseAnalytics.Param.SCREEN_CLASS, screenClass)
                
                // 添加额外参数
                additionalParams.forEach { (key, value) ->
                    when (value) {
                        is String -> putString(key, value)
                        is Int -> putInt(key, value)
                        is Long -> putLong(key, value)
                        is Double -> putDouble(key, value)
                        is Float -> putFloat(key, value)
                        is Boolean -> putBoolean(key, value)
                        else -> putString(key, value.toString())
                    }
                }
            }
            
            analytics.logEvent(FirebaseAnalytics.Event.SCREEN_VIEW, bundle)
            
            EasyLog.log("FirebaseAnalytics - 页面跟踪: $screenName ($screenClass)")
            
        } catch (e: Exception) {
            EasyLog.log("FirebaseAnalytics - 页面跟踪失败: ${e.message}", EasyLog.ERROR)
        }
    }
    
    /**
     * 跟踪用户行为事件
     * @param eventName 事件名称
     * @param params 事件参数
     */
    fun trackEvent(eventName: String, params: Map<String, Any> = emptyMap()) {
        try {
            val analytics = firebaseAnalytics
            if (analytics == null) {
                EasyLog.log("FirebaseAnalyticsHelper - 未初始化，跳过事件跟踪", EasyLog.WARN)
                return
            }
            
            val bundle = Bundle().apply {
                params.forEach { (key, value) ->
                    when (value) {
                        is String -> putString(key, value)
                        is Int -> putInt(key, value)
                        is Long -> putLong(key, value)
                        is Double -> putDouble(key, value)
                        is Float -> putFloat(key, value)
                        is Boolean -> putBoolean(key, value)
                        else -> putString(key, value.toString())
                    }
                }
            }
            
            analytics.logEvent(eventName, bundle)
            
            EasyLog.log("FirebaseAnalytics - 事件跟踪: $eventName")
            
        } catch (e: Exception) {
            EasyLog.log("FirebaseAnalytics - 事件跟踪失败: ${e.message}", EasyLog.ERROR)
        }
    }
    
    /**
     * 设置用户属性
     * @param name 属性名
     * @param value 属性值
     */
    fun setUserProperty(name: String, value: String) {
        try {
            val analytics = firebaseAnalytics
            if (analytics == null) {
                EasyLog.log("FirebaseAnalyticsHelper - 未初始化，跳过用户属性设置", EasyLog.WARN)
                return
            }
            
            analytics.setUserProperty(name, value)
            EasyLog.log("FirebaseAnalytics - 用户属性设置: $name = $value")
        } catch (e: Exception) {
            EasyLog.log("FirebaseAnalytics - 用户属性设置失败: ${e.message}", EasyLog.ERROR)
        }
    }
    
    /**
     * 设置用户ID
     * @param userId 用户ID
     */
    fun setUserId(userId: String) {
        try {
            val analytics = firebaseAnalytics
            if (analytics == null) {
                EasyLog.log("FirebaseAnalyticsHelper - 未初始化，跳过用户ID设置", EasyLog.WARN)
                return
            }
            
            analytics.setUserId(userId)
            EasyLog.log("FirebaseAnalytics - 用户ID设置: $userId")
        } catch (e: Exception) {
            EasyLog.log("FirebaseAnalytics - 用户ID设置失败: ${e.message}", EasyLog.ERROR)
        }
    }
}