package ai.sxwl.android.firebase

import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import android.content.Context
import android.os.Build
import androidx.startup.Initializer
import com.google.firebase.analytics.FirebaseAnalytics
import java.lang.reflect.Method

/** Firebase初始化器 在应用启动时自动初始化Firebase服务 */
class FirebaseInitializer : Initializer<FirebaseManager> {

    override fun create(context: Context): FirebaseManager {
        LogUtils.d(TAG, "Initializing Firebase services...")

        try {
            FirebaseManager.initialize(context)

            if (AppUtils.isAppDebug()) {
                // 调试模式下启用 Analytics 收集
                FirebaseAnalytics.getInstance(context).setAnalyticsCollectionEnabled(true)

                // 启用 Firebase DebugView（用于实时查看事件和参数）
                enableFirebaseDebugView(context)
            }

            LogUtils.d(TAG, "Firebase services initialized successfully")
        } catch (e: Exception) {
            LogUtils.e(TAG, "Failed to initialize Firebase services", e)
        }

        return FirebaseManager
    }

    override fun dependencies(): List<Class<out Initializer<*>>> {
        return emptyList()
    }

    /**
     * 启用 Firebase DebugView
     *
     * 注意：DebugView 也可以通过 adb 命令启用：
     * adb shell setprop debug.firebase.analytics.app com.ai.intellimate
     *
     * 或者在 Firebase 控制台启用：
     * 1. 登录 Firebase 控制台
     * 2. 选择项目
     * 3. 导航到 Analytics > DebugView
     * 4. 添加调试设备
     */
    private fun enableFirebaseDebugView(context: Context) {
        try {
            // 方法1：通过系统属性启用（推荐）
            val packageName = context.packageName
            setSystemProperty("debug.firebase.analytics.app", packageName)

            LogUtils.i(TAG, "✅ Firebase DebugView 已启用（通过系统属性）")
            LogUtils.i(TAG, "   包名: $packageName")
            LogUtils.i(TAG, "   在 Firebase 控制台的 DebugView 中查看实时事件")
        } catch (e: Exception) {
            LogUtils.w(TAG, "⚠️ 无法通过代码启用 DebugView，请使用 adb 命令：")
            LogUtils.w(
                TAG,
                "   adb shell setprop debug.firebase.analytics.app ${context.packageName}"
            )
            LogUtils.w(TAG, "   错误: ${e.message}")
        }
    }

    /**
     * 设置系统属性（用于启用 DebugView）
     */
    private fun setSystemProperty(key: String, value: String) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR1) {
                // Android 4.2+ 使用 SystemProperties 类
                val systemPropertiesClass = Class.forName("android.os.SystemProperties")
                val setMethod: Method =
                    systemPropertiesClass.getMethod("set", String::class.java, String::class.java)
                setMethod.invoke(null, key, value)
            } else {
                // 旧版本 Android 使用反射设置
                val runtime = Runtime.getRuntime()
                runtime.exec("setprop $key $value")
            }
        } catch (e: Exception) {
            // 如果无法设置系统属性，抛出异常让调用者处理
            throw Exception("无法设置系统属性 $key=$value: ${e.message}", e)
        }
    }

    companion object {
        private const val TAG = "FirebaseInitializer"
    }
}
