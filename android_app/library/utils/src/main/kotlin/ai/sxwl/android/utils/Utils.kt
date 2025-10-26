package ai.sxwl.android.utils

import android.app.Activity
import android.app.Application
import android.util.Log
import androidx.lifecycle.Lifecycle

/** 工具类核心类，提供应用初始化和基础功能 */
object Utils {

    private var sApp: Application? = null

    /**
     * 初始化工具类
     *
     * @param app Application实例
     */
    fun init(app: Application?) {
        if (app == null) {
            Log.e("Utils", "app is null.")
            return
        }
        if (sApp == null) {
            sApp = app
            UtilsBridge.init(app)
            return
        }
        if (sApp == app) return
        UtilsBridge.unInit(sApp!!)
        sApp = app
        UtilsBridge.init(app)
    }

    /**
     * 获取Application实例
     *
     * @return Application实例
     */
    fun getApp(): Application {
        if (sApp != null) return sApp!!

        // 尝试反射获取Application
        val reflectedApp = UtilsBridge.getApplicationByReflect()
        if (reflectedApp != null) {
            init(reflectedApp)
            if (sApp != null) {
                Log.i("Utils", UtilsBridge.getCurrentProcessName() + " reflect app success.")
                return sApp!!
            }
        }

        // 如果反射失败，抛出更明确的异常
        throw IllegalStateException(
            "Failed to initialize Application. Please call Utils.init() in Application.onCreate()"
        )
    }

    // /////////////////////////////////////////////////////////////////////////
    // interface
    // /////////////////////////////////////////////////////////////////////////

    abstract class Task<Result> {
        private var mConsumer: Consumer<Result>? = null

        constructor(consumer: Consumer<Result>?) {
            mConsumer = consumer
        }

        fun onSuccess(result: Result) {
            mConsumer?.accept(result)
        }

        abstract fun doInBackground(): Result
    }

    interface OnAppStatusChangedListener {
        fun onForeground(activity: Activity)

        fun onBackground(activity: Activity)
    }

    open class ActivityLifecycleCallbacks {
        open fun onActivityCreated(activity: Activity) {}

        open fun onActivityStarted(activity: Activity) {}

        open fun onActivityResumed(activity: Activity) {}

        open fun onActivityPaused(activity: Activity) {}

        open fun onActivityStopped(activity: Activity) {}

        open fun onActivityDestroyed(activity: Activity) {}

        open fun onLifecycleChanged(activity: Activity, event: Lifecycle.Event) {}
    }

    interface Consumer<T> {
        fun accept(t: T)
    }

    interface Supplier<T> {
        fun get(): T
    }

    interface Func1<Ret, Par> {
        fun call(param: Par): Ret
    }
}
