package com.ai.inty.utils

import android.app.Activity
import android.view.WindowManager
import com.ai.inty.BuildConfig

/**
 * 安全工具类，提供防止截屏和录屏的功能
 * 简化版本：只在聊天页面启用安全模式
 */
object SecurityUtils {

    /**
     * 启用安全模式，防止截屏和录屏
     */
    fun enableSecureMode(activity: Activity) {
        //仅在release构建渠道启用 防截屏，测试环境保留，便于反馈问题。
        if (BuildConfig.BUILD_TYPE.equals("release", true)) {
            activity.window.setFlags(
                WindowManager.LayoutParams.FLAG_SECURE,
                WindowManager.LayoutParams.FLAG_SECURE
            )
        }
    }

    /**
     * 禁用安全模式，允许截屏和录屏
     */
    fun disableSecureMode(activity: Activity) {
        activity.window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
    }

    /**
     * 检查是否启用了安全模式
     */
    fun isSecureModeEnabled(activity: Activity): Boolean {
        return (activity.window.attributes.flags and WindowManager.LayoutParams.FLAG_SECURE) != 0
    }
}
