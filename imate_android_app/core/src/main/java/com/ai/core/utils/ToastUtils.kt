package com.ai.core.utils

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.widget.Toast
import androidx.annotation.StringRes
import java.lang.ref.WeakReference

/**
 * Toast工具类
 *
 * 特性：
 * 1. 线程安全：支持在任意线程调用
 * 2. 防止重复显示：避免快速点击导致的Toast堆积
 * 3. 长文本支持：自动处理长文本的显示
 * 4. 内存安全：使用WeakReference避免内存泄漏
 * 5. 优雅降级：在异常情况下提供兜底方案
 *
 * 使用示例：
 *
 * ```kotlin
 * // 短时间显示
 * ToastUtils.showShort("操作成功")
 *
 * // 长时间显示
 * ToastUtils.showLong("网络连接失败，请检查网络设置")
 *
 * // 长文本显示（自动换行）
 * ToastUtils.showLargeText("这是一段很长的文本内容，会自动换行显示...")
 * ```
 */
object ToastUtils {

    private const val TAG = "ToastUtils"

    // 防止重复显示的间隔时间（毫秒）
    private const val MIN_INTERVAL = 1000L

    // 上次显示Toast的时间戳（使用volatile确保线程安全）
    @Volatile private var lastShowTime = 0L

    // 主线程Handler，用于线程安全
    private val mainHandler by lazy { Handler(Looper.getMainLooper()) }

    // 当前显示的Toast引用，用于取消之前的Toast
    private var currentToast: WeakReference<Toast>? = null

    /**
     * 显示短时间Toast（2秒）
     *
     * @param message 要显示的消息
     */
    @JvmStatic
    fun showShort(message: String) {
        showToast(message, Toast.LENGTH_SHORT)
    }

    /**
     * 显示短时间Toast（2秒）
     *
     * @param messageResId 要显示的消息资源ID
     */
    @JvmStatic
    fun showShort(@StringRes messageResId: Int) {
        showToast(getString(messageResId), Toast.LENGTH_SHORT)
    }

    /**
     * 显示短时间Toast（2秒），支持格式化参数
     *
     * @param messageResId 要显示的消息资源ID（可含 %1$d 等占位符）
     * @param formatArgs 格式化参数
     */
    @JvmStatic
    fun showShort(@StringRes messageResId: Int, vararg formatArgs: Any) {
        showToast(getString(messageResId, *formatArgs), Toast.LENGTH_SHORT)
    }

    /**
     * 显示长时间Toast（3.5秒）
     *
     * @param message 要显示的消息
     */
    @JvmStatic
    fun showLong(message: String) {
        showToast(message, Toast.LENGTH_LONG)
    }

    /**
     * 显示长时间Toast（3.5秒）
     *
     * @param messageResId 要显示的消息资源ID
     */
    @JvmStatic
    fun showLong(@StringRes messageResId: Int) {
        showToast(getString(messageResId), Toast.LENGTH_LONG)
    }

    /**
     * 显示长文本Toast（自动换行）
     *
     * @param message 要显示的长文本消息
     */
    @JvmStatic
    fun showLargeText(message: String) {
        showLargeTextToast(message, Toast.LENGTH_LONG)
    }

    /**
     * 显示长文本Toast（自动换行）
     *
     * @param messageResId 要显示的长文本消息资源ID
     */
    @JvmStatic
    fun showLargeText(@StringRes messageResId: Int) {
        showLargeTextToast(getString(messageResId), Toast.LENGTH_LONG)
    }

    /** 取消当前显示的Toast */
    @JvmStatic
    fun cancel() {
        currentToast?.get()?.cancel()
        currentToast = null
    }

    /**
     * 核心显示方法
     *
     * @param message 消息内容
     * @param duration 显示时长
     */
    private fun showToast(message: String, duration: Int) {
        if (message.isBlank()) {
            return
        }

        // 检查是否在最小间隔内重复显示
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastShowTime < MIN_INTERVAL) {
            return
        }

        // 线程安全处理
        if (Looper.myLooper() == Looper.getMainLooper()) {
            showToastInternal(message, duration)
        } else {
            mainHandler.post { showToastInternal(message, duration) }
        }
    }

    /** 内部显示方法 */
    private fun showToastInternal(message: String, duration: Int) {
        try {
            // 取消之前的Toast
            cancel()

            // 创建新的Toast
            val context = safeAppContext()
            if (context == null) {
                Log.e(TAG, "Context为null，无法显示Toast: $message")
                return
            }

            val toast = Toast.makeText(context, message, duration)

            // 注意：setGravity() 不应在文本 Toast 上调用，会导致警告
            // 文本 Toast 使用系统默认位置即可
            // Android API level 30 (Android 11) 或更新，
            // setGravity() 在标准文本Toast上调用是无效的。

            // 显示Toast
            toast.show()

            // 保存引用和时间戳
            currentToast = WeakReference(toast)
            lastShowTime = System.currentTimeMillis()
        } catch (e: SecurityException) {
            // 权限异常，记录日志但不降级
            Log.e(TAG, "Toast显示权限异常: $message", e)
        } catch (e: IllegalStateException) {
            // 状态异常，尝试降级
            Log.w(TAG, "Toast状态异常，尝试降级: $message", e)
            fallbackToast(message, duration)
        } catch (e: Exception) {
            // 其他异常，记录日志并降级
            Log.e(TAG, "Toast显示异常: $message", e)
            fallbackToast(message, duration)
        }
    }

    /** 显示长文本Toast（自定义布局） */
    private fun showLargeTextToast(message: String, duration: Int) {
        if (message.isBlank()) {
            return
        }

        // 检查是否在最小间隔内重复显示
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastShowTime < MIN_INTERVAL) {
            return
        }

        // 线程安全处理
        if (Looper.myLooper() == Looper.getMainLooper()) {
            showLargeTextToastInternal(message, duration)
        } else {
            mainHandler.post { showLargeTextToastInternal(message, duration) }
        }
    }

    /** 内部长文本显示方法 */
    private fun showLargeTextToastInternal(message: String, duration: Int) {
        try {
            // 取消之前的Toast
            cancel()

            val context = safeAppContext()
            if (context == null) {
                Log.e(TAG, "Context为null，无法显示长文本Toast: $message")
                return
            }

            // 对于长文本，直接使用系统Toast，但设置更长的显示时间
            // 这样可以避免使用已废弃的toast.view属性
            val toast = Toast.makeText(context, message, duration)

            // 显示Toast
            toast.show()

            // 保存引用和时间戳
            currentToast = WeakReference(toast)
            lastShowTime = System.currentTimeMillis()
        } catch (e: SecurityException) {
            // 权限异常，记录日志但不降级
            Log.e(TAG, "长文本Toast显示权限异常: $message", e)
        } catch (e: IllegalStateException) {
            // 状态异常，尝试降级
            Log.w(TAG, "长文本Toast状态异常，尝试降级: $message", e)
            showToastInternal(message, duration)
        } catch (e: Exception) {
            // 其他异常，记录日志并降级
            Log.e(TAG, "长文本Toast显示异常: $message", e)
            showToastInternal(message, duration)
        }
    }

    /** 兜底Toast方法 */
    private fun fallbackToast(message: String, duration: Int) {
        try {
            val context = safeAppContext()
            if (context != null) {
                Toast.makeText(context, message, duration).show()
            } else {
                Log.e(TAG, "Context为null，无法显示Toast: $message")
            }
        } catch (e: SecurityException) {
            // 权限异常，记录日志
            Log.e(TAG, "兜底Toast权限异常: $message", e)
        } catch (e: Exception) {
            // 最后的兜底方案：使用系统默认Toast
            try {
                val appContext = safeAppContext()?.applicationContext
                if (appContext != null) {
                    Toast.makeText(appContext, message, duration).show()
                } else {
                    Log.e(TAG, "ApplicationContext为null，无法显示Toast: $message")
                }
            } catch (e2: SecurityException) {
                // 权限异常，记录日志
                Log.e(TAG, "兜底Toast权限异常: $message", e2)
            } catch (e2: Exception) {
                // 如果连系统Toast都失败了，至少记录日志
                Log.e(TAG, "Toast显示失败: $message", e2)
            }
        }
    }

    /** 获取字符串资源 */
    private fun getString(@StringRes resId: Int): String {
        return try {
            val context = safeAppContext()
            context?.getString(resId) ?: "Unknown"
        } catch (e: Exception) {
            Log.e(TAG, "获取字符串资源失败: $resId", e)
            "Unknown"
        }
    }

    /** 获取带格式化参数的字符串资源 */
    private fun getString(@StringRes resId: Int, vararg formatArgs: Any): String {
        return try {
            val context = safeAppContext()
            context?.getString(resId, *formatArgs) ?: "Unknown"
        } catch (e: Exception) {
            Log.e(TAG, "获取字符串资源失败: $resId", e)
            "Unknown"
        }
    }

    private fun safeAppContext(): Context? = runCatching { Utils.getApp() }.getOrNull()
}
