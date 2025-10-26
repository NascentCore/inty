package ai.sxwl.android.utils

import androidx.annotation.StringRes

/**
 * 错误显示工具类
 * 
 * 提供统一的错误消息显示功能，支持字符串资源和格式化参数
 * 
 * 特性：
 * 1. 支持字符串资源ID和格式化参数
 * 2. 统一的错误显示接口
 * 3. 线程安全
 * 4. 内存安全
 * 
 * 使用示例：
 * 
 * ```kotlin
 * // 显示简单错误消息
 * ErrorDisplayUtils.showError(R.string.error_network_failed)
 * 
 * // 显示带格式化参数的错误消息
 * ErrorDisplayUtils.showError(R.string.error_format, "网络连接失败")
 * 
 * // 显示多个格式化参数的错误消息
 * ErrorDisplayUtils.showError(R.string.error_multiple_format, "网络", "超时")
 * ```
 */
object ErrorDisplayUtils {

    /**
     * 显示错误消息（使用字符串资源）
     *
     * @param errorResId 错误消息的字符串资源ID
     */
    @JvmStatic
    fun showError(@StringRes errorResId: Int) {
        ToastUtils.showShort(errorResId)
    }

    /**
     * 显示错误消息（使用字符串资源和格式化参数）
     *
     * @param errorResId 错误消息的字符串资源ID
     * @param formatArgs 格式化参数
     */
    @JvmStatic
    fun showError(@StringRes errorResId: Int, vararg formatArgs: Any) {
        try {
            val context = Utils.getApp()
            val message = context.getString(errorResId, *formatArgs)
            ToastUtils.showShort(message)
        } catch (e: Exception) {
            // 如果获取字符串资源失败，显示默认错误消息
            ToastUtils.showShort("Error occurred")
        }
    }

    /**
     * 显示错误消息（使用字符串）
     *
     * @param errorMessage 错误消息字符串
     */
    @JvmStatic
    fun showError(errorMessage: String?) {
        errorMessage?.let { 
            ToastUtils.showShort(it) 
        }
    }

    /**
     * 显示长时间错误消息（使用字符串资源）
     *
     * @param errorResId 错误消息的字符串资源ID
     */
    @JvmStatic
    fun showLongError(@StringRes errorResId: Int) {
        ToastUtils.showLong(errorResId)
    }

    /**
     * 显示长时间错误消息（使用字符串资源和格式化参数）
     *
     * @param errorResId 错误消息的字符串资源ID
     * @param formatArgs 格式化参数
     */
    @JvmStatic
    fun showLongError(@StringRes errorResId: Int, vararg formatArgs: Any) {
        try {
            val context = Utils.getApp()
            val message = context.getString(errorResId, *formatArgs)
            ToastUtils.showLong(message)
        } catch (e: Exception) {
            // 如果获取字符串资源失败，显示默认错误消息
            ToastUtils.showLong("Error occurred")
        }
    }

    /**
     * 显示长时间错误消息（使用字符串）
     *
     * @param errorMessage 错误消息字符串
     */
    @JvmStatic
    fun showLongError(errorMessage: String?) {
        errorMessage?.let { 
            ToastUtils.showLong(it) 
        }
    }
}
