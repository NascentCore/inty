package com.ai.intellimate.tips

import android.app.Activity
import android.app.Application
import android.os.Bundle

/**
 * CREATED_BY_AGENT: cursor-gpt-5.2
 *
 * 用于定义“会话（session）”边界：从用户把 App 打开到把 App 切到后台。
 *
 * 设计说明：
 * - 不能用 MainActivity 的 onPause/onStop 作为“进后台”的判断，因为 App 内部 Activity 跳转也会触发。
 * - 这里用 ActivityLifecycleCallbacks 统计 started activity 数量：
 *   - 从 0 -> 1：进入前台
 *   - 从 1 -> 0：进入后台（一个 session 结束）
 */
object IntelliMateTipsForegroundSessionTracker : Application.ActivityLifecycleCallbacks {

    private val lock = Any()
    private var installed = false
    private var startedActivitiesCount = 0

    fun install(application: Application) {
        synchronized(lock) {
            if (installed) return
            installed = true
        }
        application.registerActivityLifecycleCallbacks(this)
    }

    override fun onActivityStarted(activity: Activity) {
        synchronized(lock) {
            if (startedActivitiesCount == 0) {
                // App 进入前台：新的 session 开始
                IntelliMateTipsSessionGate.resetForNewSession()
            }
            startedActivitiesCount += 1
        }
    }

    override fun onActivityStopped(activity: Activity) {
        synchronized(lock) {
            startedActivitiesCount = (startedActivitiesCount - 1).coerceAtLeast(0)
            // started 数量归零 => App 进入后台：session 结束
            // 注意：不在后台时重置 session gate，只在进入前台时重置（见 onActivityStarted）
            // 这样可以确保在一个完整的 foreground-background-foreground 周期内只显示一次 tip
        }
    }

    override fun onActivityCreated(activity: Activity, savedInstanceState: Bundle?) {}
    override fun onActivityResumed(activity: Activity) {}
    override fun onActivityPaused(activity: Activity) {}
    override fun onActivitySaveInstanceState(activity: Activity, outState: Bundle) {}
    override fun onActivityDestroyed(activity: Activity) {}
}
