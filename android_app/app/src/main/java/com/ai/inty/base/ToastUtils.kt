package com.ai.inty.base

import android.content.Context
import android.util.Log
import android.widget.Toast
import com.inty.utils.AppEnv
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.ConcurrentHashMap

object ToastUtils {

    // 缓存最近显示的 Toast 信息，避免重复显示
    private val lastToastInfo = ConcurrentHashMap<String, Long>()

    // 防重复时间间隔（毫秒），默认 2 秒
    @Volatile
    private var debounceTimeMs: Long = 2000L

    // 最大缓存数量，避免内存泄漏
    private const val MAX_CACHE_SIZE = 50

    // 缓存清理阈值
    private const val CACHE_CLEANUP_THRESHOLD = 30

    /**
     * 检查是否应该显示 Toast（防重复）
     */
    private fun shouldShowToast(message: String): Boolean {
        val currentTime = System.currentTimeMillis()
        val lastTime = lastToastInfo[message] ?: 0L

        // 如果距离上次显示时间超过防重复间隔，则允许显示
        if (currentTime - lastTime > debounceTimeMs) {
            // 更新显示时间
            lastToastInfo[message] = currentTime

            // 清理过期的缓存项，避免内存泄漏
            cleanupCache(currentTime)

            return true
        }

        return false
    }

    /**
     * 清理过期的缓存项
     */
    private fun cleanupCache(currentTime: Long) {
        if (lastToastInfo.size > CACHE_CLEANUP_THRESHOLD) {
            val expiredKeys = lastToastInfo.entries
                .filter { currentTime - it.value > debounceTimeMs * 2 }
                .map { it.key }

            expiredKeys.forEach { lastToastInfo.remove(it) }

            // 如果缓存仍然过大，强制清理最旧的项目
            if (lastToastInfo.size > MAX_CACHE_SIZE) {
                val sortedEntries = lastToastInfo.entries.sortedBy { it.value }
                val itemsToRemove = sortedEntries.take(lastToastInfo.size - MAX_CACHE_SIZE)
                itemsToRemove.forEach { lastToastInfo.remove(it.key) }
            }
        }
    }

    /**
     * 安全地创建 Toast
     */
    private fun createSafeToast(context: Context, message: String, duration: Int): Toast? {
        return try {
            Toast.makeText(context, message, duration)
        } catch (e: Exception) {
            Log.e("ToastUtils", "createSafeToast error: ${e.message}")
            null
        }
    }

    /**
     * 显示 Toast 消息（带防重复功能）
     * @param msg 要显示的消息
     */
    suspend fun showToast(msg: String) = withContext(Dispatchers.Main) {
        try {
            val context: Context? = AppEnv.context
            if (context != null && msg.isNotEmpty() && shouldShowToast(msg)) {
                val toast = createSafeToast(context, msg, Toast.LENGTH_SHORT)
                toast?.show()
            }
        } catch (e: Exception) {
            Log.e("ToastUtils", "showToast error: ${e.message}")
        }
    }

    /**
     * 显示 Toast 消息（通过资源ID，带防重复功能）
     * @param stringResId 字符串资源ID
     */
    suspend fun showToast(stringResId: Int) = withContext(Dispatchers.Main) {
        try {
            val context: Context? = AppEnv.context
            if (context != null) {
                val message = context.getString(stringResId)
                if (message.isNotEmpty() && shouldShowToast(message)) {
                    val toast = createSafeToast(context, message, Toast.LENGTH_SHORT)
                    toast?.show()
                }
            }
        } catch (e: Exception) {
            Log.e("ToastUtils", "showToast error: ${e.message}")
        }
    }

    /**
     * 显示 Toast 消息（带格式化参数，带防重复功能）
     * @param stringResId 字符串资源ID
     * @param formatArgs 格式化参数
     */
    suspend fun showToast(stringResId: Int, vararg formatArgs: Any) =
        withContext(Dispatchers.Main) {
            try {
                val context: Context? = AppEnv.context
                if (context != null) {
                    val message = context.getString(stringResId, *formatArgs)
                    if (message.isNotEmpty() && shouldShowToast(message)) {
                        val toast = createSafeToast(context, message, Toast.LENGTH_SHORT)
                        toast?.show()
                    }
                }
            } catch (e: Exception) {
                Log.e("ToastUtils", "showToast error: ${e.message}")
            }
        }

    /**
     * 强制显示 Toast（忽略防重复检查）
     * @param msg 要显示的消息
     */
    suspend fun showToastForce(msg: String) = withContext(Dispatchers.Main) {
        try {
            val context: Context? = AppEnv.context
            if (context != null && msg.isNotEmpty()) {
                val toast = createSafeToast(context, msg, Toast.LENGTH_SHORT)
                toast?.show()
            }
        } catch (e: Exception) {
            Log.e("ToastUtils", "showToastForce error: ${e.message}")
        }
    }

    /**
     * 强制显示 Toast（忽略防重复检查）
     * @param stringResId 字符串资源ID
     */
    suspend fun showToastForce(stringResId: Int) = withContext(Dispatchers.Main) {
        try {
            val context: Context? = AppEnv.context
            if (context != null) {
                val message = context.getString(stringResId)
                if (message.isNotEmpty()) {
                    val toast = createSafeToast(context, message, Toast.LENGTH_SHORT)
                    toast?.show()
                }
            }
        } catch (e: Exception) {
            Log.e("ToastUtils", "showToastForce error: ${e.message}")
        }
    }

    /**
     * 显示长时长的 Toast（带防重复功能）
     * @param msg 要显示的消息
     */
    suspend fun showLongToast(msg: String) = withContext(Dispatchers.Main) {
        try {
            val context: Context? = AppEnv.context
            if (context != null && msg.isNotEmpty() && shouldShowToast(msg)) {
                val toast = createSafeToast(context, msg, Toast.LENGTH_LONG)
                toast?.show()
            }
        } catch (e: Exception) {
            Log.e("ToastUtils", "showLongToast error: ${e.message}")
        }
    }

    /**
     * 显示长时长的 Toast（通过资源ID，带防重复功能）
     * @param stringResId 字符串资源ID
     */
    suspend fun showLongToast(stringResId: Int) = withContext(Dispatchers.Main) {
        try {
            val context: Context? = AppEnv.context
            if (context != null) {
                val message = context.getString(stringResId)
                if (message.isNotEmpty() && shouldShowToast(message)) {
                    val toast = createSafeToast(context, message, Toast.LENGTH_LONG)
                    toast?.show()
                }
            }
        } catch (e: Exception) {
            Log.e("ToastUtils", "showLongToast error: ${e.message}")
        }
    }

    /**
     * 清除 Toast 缓存
     */
    fun clearToastCache() {
        lastToastInfo.clear()
        Log.d("ToastUtils", "Toast cache cleared")
    }

    /**
     * 设置防重复时间间隔
     * @param debounceTimeMs 防重复时间间隔（毫秒）
     */
    fun setDebounceTime(debounceTimeMs: Long) {
        if (debounceTimeMs > 0) {
            this.debounceTimeMs = debounceTimeMs
            Log.d("ToastUtils", "Debounce time set to: ${debounceTimeMs}ms")
        }
    }

    /**
     * 获取当前防重复时间间隔
     */
    fun getDebounceTime(): Long {
        return debounceTimeMs
    }

    /**
     * 获取当前缓存大小
     */
    fun getCacheSize(): Int {
        return lastToastInfo.size
    }

    /**
     * 检查指定消息是否在防重复期内
     * @param message 要检查的消息
     * @return true 如果在防重复期内，false 否则
     */
    fun isInDebouncePeriod(message: String): Boolean {
        val currentTime = System.currentTimeMillis()
        val lastTime = lastToastInfo[message] ?: 0L
        return currentTime - lastTime <= debounceTimeMs
    }
}
