package com.ai.inty.utils

import com.ai.inty.beans.SysMsgItem
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

/**
 * 系统消息缓存管理器
 * 负责缓存系统消息数据
 */
object SystemMessageCacheManager {

    private const val KEY_SYSTEM_MESSAGES = "cached_system_messages"
    private const val KEY_SYSTEM_MESSAGES_TIMESTAMP = "system_messages_cache_timestamp"
    private const val CACHE_EXPIRY_TIME = 15 * 60 * 1000L // 15分钟缓存过期时间

    private val moshi = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()

    private val sysMsgListType =
        Types.newParameterizedType(List::class.java, SysMsgItem::class.java)
    private val sysMsgListAdapter = moshi.adapter<List<SysMsgItem>>(sysMsgListType)

    /**
     * 缓存系统消息
     */
    fun cacheSystemMessages(messages: List<SysMsgItem>) {
        try {
            val messagesJson = sysMsgListAdapter.toJson(messages)
            IntySetting.setUserProfileData(KEY_SYSTEM_MESSAGES, messagesJson)
            IntySetting.setUserProfileData(
                KEY_SYSTEM_MESSAGES_TIMESTAMP,
                System.currentTimeMillis().toString()
            )
            EasyLog.log("SystemMessageCacheManager - 缓存系统消息成功: ${messages.size}条")
        } catch (e: Exception) {
            EasyLog.log("SystemMessageCacheManager - 缓存系统消息失败: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 获取缓存的系统消息
     */
    fun getCachedSystemMessages(): List<SysMsgItem> {
        return try {
            val messagesJson = IntySetting.getUserProfileData(KEY_SYSTEM_MESSAGES)
            if (messagesJson.isNullOrEmpty()) {
                emptyList()
            } else {
                val messages = sysMsgListAdapter.fromJson(messagesJson) ?: emptyList()
                EasyLog.log("SystemMessageCacheManager - 获取缓存系统消息: ${messages.size}条")
                messages
            }
        } catch (e: Exception) {
            EasyLog.log(
                "SystemMessageCacheManager - 获取缓存系统消息失败: ${e.message}",
                EasyLog.ERROR
            )
            emptyList()
        }
    }

    /**
     * 检查缓存是否过期
     */
    fun isCacheExpired(): Boolean {
        val timestampStr = IntySetting.getUserProfileData(KEY_SYSTEM_MESSAGES_TIMESTAMP)
        if (timestampStr.isNullOrEmpty()) {
            return true
        }

        return try {
            val timestamp = timestampStr.toLong()
            val currentTime = System.currentTimeMillis()
            val isExpired = (currentTime - timestamp) > CACHE_EXPIRY_TIME
            EasyLog.log("SystemMessageCacheManager - 缓存过期检查: ${if (isExpired) "已过期" else "未过期"}")
            isExpired
        } catch (e: Exception) {
            EasyLog.log("SystemMessageCacheManager - 检查缓存过期失败: ${e.message}", EasyLog.ERROR)
            true
        }
    }

    /**
     * 添加新的系统消息到缓存
     */
    fun addSystemMessage(message: SysMsgItem) {
        try {
            val messages = getCachedSystemMessages().toMutableList()
            // 检查是否已存在
            val existingIndex = messages.indexOfFirst { it.id == message.id }
            if (existingIndex != -1) {
                messages[existingIndex] = message
            } else {
                messages.add(0, message) // 添加到开头
            }
            cacheSystemMessages(messages)
            EasyLog.log("SystemMessageCacheManager - 添加系统消息到缓存: ${message.title}")
        } catch (e: Exception) {
            EasyLog.log("SystemMessageCacheManager - 添加系统消息失败: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 标记系统消息为已读
     */
    fun markMessageAsRead(messageId: String) {
        try {
            val messages = getCachedSystemMessages().toMutableList()
            val messageIndex = messages.indexOfFirst { it.id == messageId }
            if (messageIndex != -1) {
                messages[messageIndex] = messages[messageIndex].copy(isRead = true)
                cacheSystemMessages(messages)
                EasyLog.log("SystemMessageCacheManager - 标记消息为已读: $messageId")
            }
        } catch (e: Exception) {
            EasyLog.log(
                "SystemMessageCacheManager - 标记消息为已读失败: ${e.message}",
                EasyLog.ERROR
            )
        }
    }

    /**
     * 获取未读消息数量
     */
    fun getUnreadMessageCount(): Int {
        return getCachedSystemMessages().count { !it.isRead }
    }

    /**
     * 清理所有缓存
     */
    fun clearCache() {
        try {
            IntySetting.setUserProfileData(KEY_SYSTEM_MESSAGES, "")
            IntySetting.setUserProfileData(KEY_SYSTEM_MESSAGES_TIMESTAMP, "")
            EasyLog.log("SystemMessageCacheManager - 缓存已清理")
        } catch (e: Exception) {
            EasyLog.log("SystemMessageCacheManager - 清理缓存失败: ${e.message}", EasyLog.ERROR)
        }
    }

    /**
     * 获取缓存统计信息
     */
    fun getCacheStats(): CacheStats {
        val messages = getCachedSystemMessages()
        val totalCount = messages.size
        val unreadCount = messages.count { !it.isRead }
        val isExpired = isCacheExpired()

        return CacheStats(
            totalMessagesCount = totalCount,
            unreadMessagesCount = unreadCount,
            isExpired = isExpired
        )
    }

    /**
     * 缓存统计信息数据类
     */
    data class CacheStats(
        val totalMessagesCount: Int,
        val unreadMessagesCount: Int,
        val isExpired: Boolean
    )
}
