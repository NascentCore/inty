package ai.sxwl.android.utils

import android.app.Application
import android.util.Log
import kotlin.random.Random

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
}

/** 以概率返回true；用于随机概率事件的触发。 */
fun pickWithProbability(probability: Float): Boolean {
    return Random.nextFloat() < probability
}
