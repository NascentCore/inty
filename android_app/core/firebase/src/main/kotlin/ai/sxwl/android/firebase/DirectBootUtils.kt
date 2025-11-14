package ai.sxwl.android.firebase

import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import android.content.Context
import android.os.Build
import android.os.UserManager

/**
 * Direct Boot 工具类
 *
 * 提供检测设备是否处于 Direct Boot 模式（用户未解锁状态）的工具方法
 *
 * 参考文档：https://firebase.google.com/docs/cloud-messaging/customize-messages/android-direct-boot?hl=zh-cn
 */
object DirectBootUtils {

    /**
     * 检查用户是否已解锁（设备是否已退出 Direct Boot 模式）
     *
     * @param context Context 实例
     * @return true 表示用户已解锁，false 表示设备处于 Direct Boot 模式
     */
    fun isUserUnlocked(context: Context? = null): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
            // Android 7.0 以下不支持 Direct Boot
            return true
        }

        return try {
            val appContext = context ?: Utils.getApp()
            val userManager = appContext.getSystemService(Context.USER_SERVICE) as? UserManager
            userManager?.isUserUnlocked ?: true
        } catch (e: Exception) {
            LogUtils.w("DirectBootUtils", "检查用户解锁状态失败，假设已解锁: ${e.message}")
            true
        }
    }

    /**
     * 检查设备是否处于 Direct Boot 模式
     *
     * @param context Context 实例
     * @return true 表示设备处于 Direct Boot 模式，false 表示用户已解锁
     */
    fun isDirectBootMode(context: Context? = null): Boolean {
        return !isUserUnlocked(context)
    }
}
