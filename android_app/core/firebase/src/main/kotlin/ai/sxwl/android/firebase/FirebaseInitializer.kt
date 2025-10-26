package ai.sxwl.android.firebase

import ai.sxwl.android.utils.LogUtils
import android.content.Context
import androidx.startup.Initializer

/** Firebase初始化器 在应用启动时自动初始化Firebase服务 */
class FirebaseInitializer : Initializer<FirebaseManager> {

    override fun create(context: Context): FirebaseManager {
        LogUtils.d(TAG, "Initializing Firebase services...")

        try {
            FirebaseManager.initialize(context)
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
