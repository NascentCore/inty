package com.ai.inty.utils

import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver

/**
 * Compose页面跟踪工具
 * 用于自动跟踪Compose页面的生命周期，在页面显示时发送Firebase Analytics事件
 */

/**
 * 使用Composable函数跟踪页面
 * 这是一个更简单的替代方案，直接在Composable函数中使用
 * @param screenName 页面名称
 * @param screenClass 页面类名
 * @param additionalParams 额外参数
 */
@Composable
fun TrackScreenView(
    screenName: String,
    screenClass: String,
    additionalParams: Map<String, Any> = emptyMap()
) {
    val lifecycleOwner = LocalLifecycleOwner.current
    
    DisposableEffect(screenName, screenClass) {
        // 页面显示时发送跟踪事件
        FirebaseAnalyticsHelper.trackScreenView(
            screenName = screenName,
            screenClass = screenClass,
            additionalParams = additionalParams
        )
        
        // 监听生命周期变化
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_RESUME -> {
                    // 页面重新显示时也发送跟踪事件
                    FirebaseAnalyticsHelper.trackScreenView(
                        screenName = screenName,
                        screenClass = screenClass,
                        additionalParams = additionalParams
                    )
                }
                else -> { /* 其他生命周期事件暂不处理 */ }
            }
        }
        
        lifecycleOwner.lifecycle.addObserver(observer)
        
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }
}

/**
 * 跟踪页面事件的Composable函数
 * @param eventName 事件名称
 * @param params 事件参数
 */
@Composable
fun TrackEvent(
    eventName: String,
    params: Map<String, Any> = emptyMap()
) {
    DisposableEffect(eventName) {
        FirebaseAnalyticsHelper.trackEvent(eventName, params)
        onDispose { /* 事件跟踪不需要清理 */ }
    }
}
