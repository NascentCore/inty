package ai.sxwl.android.firebase

import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import androidx.core.content.edit

/**
 * Direct Boot 存储管理器
 *
 * 使用设备加密存储（Device Encrypted Storage）的 SharedPreferences
 * 在 Direct Boot 模式下（用户未解锁）可以访问
 *
 * 实现方式：
 * - 使用 Context.createDeviceProtectedStorageContext() 创建设备加密存储 Context
 * - 在该 Context 上使用普通的 SharedPreferences
 * - 不依赖已弃用的 androidx.security:security-crypto
 *
 * 注意：
 * - 设备加密存储的安全性低于凭据加密存储
 * - 仅存储 Direct Boot 模式下必需的轻量数据（如消息 ID、时间戳等）
 * - 敏感数据应在用户解锁后迁移到凭据加密存储
 *
 * 参考文档：https://firebase.google.com/docs/cloud-messaging/customize-messages/android-direct-boot?hl=zh-cn
 */
object DirectBootStorage {

    private const val PREFS_NAME = "direct_boot_prefs"
    private const val KEY_PENDING_MESSAGES = "pending_messages"
    private const val KEY_MESSAGE_COUNT = "message_count"

    @Volatile
    private var deviceProtectedPrefs: SharedPreferences? = null

    /**
     * 数据类：待处理的消息元数据
     */
    data class PendingMessage(
        val messageId: String,
        val timestamp: Long,
        val type: String?,
        val agentId: String?,
        val title: String?,
        val body: String?,
    )

    /**
     * 初始化 Direct Boot 存储
     * 使用设备加密存储 Context 创建 SharedPreferences
     *
     * 注意：不缓存 Context 以避免内存泄漏，只缓存 SharedPreferences 实例
     */
    fun initialize(context: Context? = null): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
            // Android 7.0 以下不支持 Direct Boot
            return false
        }

        if (deviceProtectedPrefs != null) {
            return true
        }

        return try {
            val appContext = context?.applicationContext ?: Utils.getApp()

            // 创建设备加密存储 Context（不缓存，避免内存泄漏）
            // 这个 Context 在 Direct Boot 模式下可以访问
            val deviceProtectedContext = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                appContext.createDeviceProtectedStorageContext()
            } else {
                appContext
            }

            // 在设备加密存储 Context 上创建 SharedPreferences
            // 只缓存 SharedPreferences 实例，不缓存 Context
            deviceProtectedPrefs = deviceProtectedContext.getSharedPreferences(
                PREFS_NAME,
                Context.MODE_PRIVATE
            )

            LogUtils.d("DirectBootStorage", "Direct Boot 存储初始化成功")
            true
        } catch (e: Exception) {
            LogUtils.e("DirectBootStorage", "Direct Boot 存储初始化失败: ${e.message}", e)
            false
        }
    }

    /**
     * 获取设备加密存储的 SharedPreferences 实例
     *
     * @param context Context 实例（用于初始化，如果尚未初始化）
     */
    private fun getPrefs(context: Context? = null): SharedPreferences? {
        if (deviceProtectedPrefs == null) {
            initialize(context)
        }
        return deviceProtectedPrefs
    }

    /**
     * 保存待处理的消息元数据
     *
     * @param message 消息元数据
     * @param context Context 实例（用于初始化，如果尚未初始化）
     */
    fun savePendingMessage(message: PendingMessage, context: Context? = null): Boolean {
        return try {
            val prefs = getPrefs(context) ?: return false

            // 获取现有的待处理消息列表
            val existingMessages = getPendingMessages(context).toMutableList()
            existingMessages.add(message)

            // 限制待处理消息数量（最多保存 50 条，避免存储膨胀）
            val trimmedMessages = if (existingMessages.size > 50) {
                existingMessages.takeLast(50)
            } else {
                existingMessages
            }

            // 将消息列表序列化为 JSON 字符串（简化实现，使用简单格式）
            val messagesJson = serializeMessages(trimmedMessages)

            prefs.edit {
                putString(KEY_PENDING_MESSAGES, messagesJson)
                    .putInt(KEY_MESSAGE_COUNT, trimmedMessages.size)
            }

            LogUtils.d(
                "DirectBootStorage",
                "保存待处理消息: messageId=${message.messageId}, 总数=${trimmedMessages.size}"
            )
            true
        } catch (e: Exception) {
            LogUtils.e("DirectBootStorage", "保存待处理消息失败: ${e.message}", e)
            false
        }
    }

    /**
     * 获取所有待处理的消息
     *
     * @param context Context 实例（用于初始化，如果尚未初始化）
     */
    fun getPendingMessages(context: Context? = null): List<PendingMessage> {
        return try {
            val prefs = getPrefs(context) ?: return emptyList()
            val messagesJson = prefs.getString(KEY_PENDING_MESSAGES, null) ?: return emptyList()
            deserializeMessages(messagesJson)
        } catch (e: Exception) {
            LogUtils.e("DirectBootStorage", "获取待处理消息失败: ${e.message}", e)
            emptyList()
        }
    }

    /**
     * 清除所有待处理的消息
     *
     * @param context Context 实例（用于初始化，如果尚未初始化）
     */
    fun clearPendingMessages(context: Context? = null): Boolean {
        return try {
            val prefs = getPrefs(context) ?: return false
            prefs.edit {
                remove(KEY_PENDING_MESSAGES)
                    .putInt(KEY_MESSAGE_COUNT, 0)
            }
            LogUtils.d("DirectBootStorage", "已清除所有待处理消息")
            true
        } catch (e: Exception) {
            LogUtils.e("DirectBootStorage", "清除待处理消息失败: ${e.message}", e)
            false
        }
    }

    /**
     * 获取待处理消息数量
     *
     * @param context Context 实例（用于初始化，如果尚未初始化）
     */
    fun getPendingMessageCount(context: Context? = null): Int {
        return try {
            val prefs = getPrefs(context) ?: return 0
            prefs.getInt(KEY_MESSAGE_COUNT, 0)
        } catch (e: Exception) {
            LogUtils.e("DirectBootStorage", "获取待处理消息数量失败: ${e.message}", e)
            0
        }
    }

    /**
     * 调试方法：打印 Direct Boot 存储状态
     * 用于测试和调试
     *
     * @param context Context 实例
     */
    fun debugPrintStatus(context: Context? = null) {
        try {
            val appContext = context?.applicationContext ?: Utils.getApp()
            val isUnlocked = DirectBootUtils.isUserUnlocked(appContext)
            val messageCount = getPendingMessageCount(context)
            val messages = getPendingMessages(context)

            LogUtils.d("DirectBootStorage", "=== Direct Boot 存储状态 ===")
            LogUtils.d("DirectBootStorage", "用户解锁状态: $isUnlocked")
            LogUtils.d("DirectBootStorage", "待处理消息数量: $messageCount")
            LogUtils.d("DirectBootStorage", "存储初始化状态: ${deviceProtectedPrefs != null}")

            if (messages.isNotEmpty()) {
                LogUtils.d("DirectBootStorage", "待处理消息列表:")
                messages.forEachIndexed { index, message ->
                    LogUtils.d(
                        "DirectBootStorage",
                        "  [$index] messageId=${message.messageId}, " +
                                "type=${message.type}, agentId=${message.agentId}, " +
                                "title=${message.title?.take(20)}..."
                    )
                }
            } else {
                LogUtils.d("DirectBootStorage", "没有待处理消息")
            }
            LogUtils.d("DirectBootStorage", "============================")
        } catch (e: Exception) {
            LogUtils.e("DirectBootStorage", "打印状态失败: ${e.message}", e)
        }
    }

    /**
     * 序列化消息列表为 JSON 字符串（简化实现）
     * 格式：messageId|timestamp|type|agentId|title|body\n...
     */
    private fun serializeMessages(messages: List<PendingMessage>): String {
        return messages.joinToString("\n") { message ->
            listOf(
                message.messageId,
                message.timestamp.toString(),
                message.type ?: "",
                message.agentId ?: "",
                message.title ?: "",
                message.body ?: "",
            ).joinToString("|") { field ->
                // 转义特殊字符
                field.replace("|", "\\|").replace("\n", "\\n")
            }
        }
    }

    /**
     * 反序列化 JSON 字符串为消息列表
     */
    private fun deserializeMessages(json: String): List<PendingMessage> {
        if (json.isEmpty()) return emptyList()

        return json.split("\n").mapNotNull { line ->
            if (line.isEmpty()) return@mapNotNull null

            try {
                val fields = line.split("|").map { field ->
                    // 反转义特殊字符
                    field.replace("\\|", "|").replace("\\n", "\n")
                }

                if (fields.size >= 6) {
                    PendingMessage(
                        messageId = fields[0],
                        timestamp = fields[1].toLongOrNull() ?: System.currentTimeMillis(),
                        type = fields[2].takeIf { it.isNotEmpty() },
                        agentId = fields[3].takeIf { it.isNotEmpty() },
                        title = fields[4].takeIf { it.isNotEmpty() },
                        body = fields[5].takeIf { it.isNotEmpty() },
                    )
                } else {
                    null
                }
            } catch (e: Exception) {
                LogUtils.w("DirectBootStorage", "解析消息失败: $line, 错误: ${e.message}")
                null
            }
        }
    }
}
