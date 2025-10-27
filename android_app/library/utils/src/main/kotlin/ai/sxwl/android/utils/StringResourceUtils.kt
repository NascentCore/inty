package ai.sxwl.android.utils

import android.util.Log
import androidx.annotation.StringRes

/**
 * 字符串资源工具类
 *
 * 提供安全的字符串资源获取功能，包含异常处理和降级方案。
 *
 * 特性：
 * 1. 异常安全：捕获所有可能的异常并提供降级方案
 * 2. 空值处理：Context为null时返回默认值
 * 3. 日志记录：记录异常信息便于调试
 * 4. 线程安全：可在任意线程调用
 *
 * 使用示例：
 *
 * ```kotlin
 * // 获取字符串资源
 * val message = StringResourceUtils.getString(R.string.app_name)
 * ```
 */
object StringResourceUtils {

    private const val TAG = "StringResourceUtils"

    /**
     * 获取字符串资源
     *
     * @param resId 字符串资源ID
     * @return 字符串资源内容，失败时返回"Unknown"
     */
    @JvmStatic
    fun getString(@StringRes resId: Int): String {
        return try {
            val context = Utils.getApp()
            if (context != null) {
                context.getString(resId)
            } else {
                Log.w(TAG, "Context为null，无法获取字符串资源: $resId")
                "Unknown"
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取字符串资源失败: $resId", e)
            "Unknown"
        }
    }
}
