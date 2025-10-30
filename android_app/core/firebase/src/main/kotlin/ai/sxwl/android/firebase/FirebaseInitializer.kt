package ai.sxwl.android.firebase

import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import android.content.Context
import androidx.startup.Initializer
import com.google.firebase.analytics.FirebaseAnalytics

/** Firebase初始化器 在应用启动时自动初始化Firebase服务 */
class FirebaseInitializer : Initializer<FirebaseManager> {

    override fun create(context: Context): FirebaseManager {
        LogUtils.d(TAG, "Initializing Firebase services...")

        try {
            FirebaseManager.initialize(context)
            // 初始化 Remote Config（A/B 实验与动态配置）
            RemoteConfigManager.initialize(context)
            if (AppUtils.isAppDebug()) {
                FirebaseAnalytics.getInstance(context).setAnalyticsCollectionEnabled(true)
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

    companion object {
        private const val TAG = "FirebaseInitializer"
    }
}
