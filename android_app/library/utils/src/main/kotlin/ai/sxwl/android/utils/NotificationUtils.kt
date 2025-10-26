package ai.sxwl.android.utils

import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.net.Uri
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.Person

/** 通知工具类 提供完整的通知管理功能，支持现代Android通知特性 */
object NotificationUtils {

    private const val TAG = "NotificationUtils"
    private const val DEFAULT_CHANNEL_ID = "default"
    private const val DEFAULT_CHANNEL_NAME = "默认通知"

    // ==================== 通知配置类 ====================

    /** 通知配置类 */
    data class NotificationConfig(
        val id: Int,
        val channelId: String = DEFAULT_CHANNEL_ID,
        val title: String,
        val content: String,
        val icon: Int = android.R.drawable.ic_dialog_info,
        val largeIcon: Bitmap? = null,
        val intent: Intent? = null,
        val priority: Int = NotificationCompat.PRIORITY_DEFAULT,
        val autoCancel: Boolean = true,
        val ongoing: Boolean = false,
        val showWhen: Boolean = true,
        val groupKey: String? = null,
        val sortKey: String? = null,
        val sound: Uri? = null,
        val vibrationPattern: LongArray? = null,
        val lights: Boolean = false,
        val lightColor: Int = Color.BLUE,
        val actions: List<NotificationAction> = emptyList(),
        val style: NotificationStyle? = null
    )

    /** 通知动作 */
    data class NotificationAction(val icon: Int, val title: String, val intent: Intent)

    /** 通知样式 */
    sealed class NotificationStyle {
        data class BigTextStyle(val bigText: String) : NotificationStyle()

        data class BigPictureStyle(val bigPicture: Bitmap, val bigLargeIcon: Bitmap? = null) :
            NotificationStyle()

        data class InboxStyle(val lines: List<String>) : NotificationStyle()

        data class MessagingStyle(
            val conversationTitle: String? = null,
            val messages: List<NotificationMessage> = emptyList()
        ) : NotificationStyle()

        data class ProgressStyle(
            val max: Int,
            val progress: Int,
            val indeterminate: Boolean = false
        ) : NotificationStyle()
    }

    /** 通知消息 */
    data class NotificationMessage(
        val text: String,
        val timestamp: Long,
        val person: Person? = null
    )

    // ==================== 通知渠道管理 ====================

    /** 创建通知渠道 */
    fun createNotificationChannel(
        channelId: String,
        channelName: String,
        importance: Int = NotificationManager.IMPORTANCE_DEFAULT,
        description: String? = null,
        sound: Uri? = null,
        vibrationPattern: LongArray? = null,
        lights: Boolean = false,
        lightColor: Int = Color.BLUE
    ): Boolean {
        return createNotificationChannel(
            Utils.getApp(),
            channelId,
            channelName,
            importance,
            description,
            sound,
            vibrationPattern,
            lights,
            lightColor
        )
    }

    /** 创建通知渠道 */
    fun createNotificationChannel(
        context: Context,
        channelId: String,
        channelName: String,
        importance: Int = NotificationManager.IMPORTANCE_DEFAULT,
        description: String? = null,
        sound: Uri? = null,
        vibrationPattern: LongArray? = null,
        lights: Boolean = false,
        lightColor: Int = Color.BLUE
    ): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return true

        return try {
            val notificationManager =
                context.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
                    ?: return false

            // 检查渠道是否已存在
            if (notificationManager.getNotificationChannel(channelId) != null) {
                Log.d(TAG, "通知渠道已存在: $channelId")
                return true
            }

            val channel =
                NotificationChannel(channelId, channelName, importance).apply {
                    this.description = description
                    this.vibrationPattern = vibrationPattern
                    this.enableLights(lights)
                    this.lightColor = lightColor

                    // 设置音频属性
                    val audioAttributes =
                        AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_NOTIFICATION)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                            .build()

                    // 设置声音
                    val notificationSound =
                        sound ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)
                    setSound(notificationSound, audioAttributes)
                }

            notificationManager.createNotificationChannel(channel)
            Log.d(TAG, "创建通知渠道成功: $channelId")
            true
        } catch (e: Exception) {
            Log.e(TAG, "创建通知渠道失败: $channelId", e)
            false
        }
    }

    /** 删除通知渠道 */
    fun deleteNotificationChannel(channelId: String): Boolean {
        return deleteNotificationChannel(Utils.getApp(), channelId)
    }

    /** 删除通知渠道 */
    fun deleteNotificationChannel(context: Context, channelId: String): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return true

        return try {
            val notificationManager =
                context.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
                    ?: return false
            notificationManager.deleteNotificationChannel(channelId)
            Log.d(TAG, "删除通知渠道成功: $channelId")
            true
        } catch (e: Exception) {
            Log.e(TAG, "删除通知渠道失败: $channelId", e)
            false
        }
    }

    // ==================== 通知显示 ====================

    /** 显示通知 */
    fun showNotification(config: NotificationConfig): Boolean {
        return showNotification(Utils.getApp(), config)
    }

    /** 显示通知 */
    @SuppressLint("MissingPermission")
    fun showNotification(context: Context, config: NotificationConfig): Boolean {
        if (!areNotificationsEnabled(context)) {
            Log.w(TAG, "通知未启用")
            return false
        }

        return try {
            // 确保通知渠道存在
            createNotificationChannel(
                context,
                config.channelId,
                getChannelName(config.channelId),
                getChannelImportance(config.priority)
            )

            val notificationManager = NotificationManagerCompat.from(context)
            val builder = buildNotificationBuilder(context, config)

            notificationManager.notify(config.id, builder.build())
            Log.d(TAG, "显示通知成功: ${config.id}")
            true
        } catch (e: Exception) {
            Log.e(TAG, "显示通知失败: ${config.id}", e)
            false
        }
    }

    /** 构建通知Builder */
    private fun buildNotificationBuilder(
        context: Context,
        config: NotificationConfig
    ): NotificationCompat.Builder {
        val builder =
            NotificationCompat.Builder(context, config.channelId)
                .setSmallIcon(config.icon)
                .setContentTitle(config.title)
                .setContentText(config.content)
                .setPriority(config.priority)
                .setAutoCancel(config.autoCancel)
                .setOngoing(config.ongoing)
                .setShowWhen(config.showWhen)

        // 设置大图标
        config.largeIcon?.let { builder.setLargeIcon(it) }

        // 设置点击意图
        config.intent?.let { intent ->
            val pendingIntent =
                try {
                    PendingIntent.getActivity(
                        context,
                        config.id,
                        intent,
                        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                    )
                } catch (e: Exception) {
                    Log.e("NotificationUtils", "创建PendingIntent失败", e)
                    null
                }
            pendingIntent?.let { builder.setContentIntent(it) }
        }

        // 设置分组
        config.groupKey?.let { builder.setGroup(it) }
        config.sortKey?.let { builder.setSortKey(it) }

        // 设置声音和振动
        config.sound?.let { builder.setSound(it) }
        config.vibrationPattern?.let { builder.setVibrate(it) }

        // 设置灯光
        if (config.lights) {
            builder.setLights(config.lightColor, 1000, 1000)
        }

        // 设置样式
        config.style?.let { style ->
            when (style) {
                is NotificationStyle.BigTextStyle -> {
                    builder.setStyle(NotificationCompat.BigTextStyle().bigText(style.bigText))
                }
                is NotificationStyle.BigPictureStyle -> {
                    val bigPictureStyle =
                        NotificationCompat.BigPictureStyle().bigPicture(style.bigPicture)
                    style.bigLargeIcon?.let { bigPictureStyle.bigLargeIcon(it) }
                    builder.setStyle(bigPictureStyle)
                }
                is NotificationStyle.InboxStyle -> {
                    val inboxStyle = NotificationCompat.InboxStyle()
                    style.lines.forEach { line -> inboxStyle.addLine(line) }
                    builder.setStyle(inboxStyle)
                }
                is NotificationStyle.MessagingStyle -> {
                    val messagingStyle =
                        if (style.conversationTitle != null) {
                            NotificationCompat.MessagingStyle(style.conversationTitle)
                        } else {
                            NotificationCompat.MessagingStyle("Unknown UserName")
                        }
                    style.messages.forEach { message ->
                        messagingStyle.addMessage(message.text, message.timestamp, message.person)
                    }
                    builder.setStyle(messagingStyle)
                }
                is NotificationStyle.ProgressStyle -> {
                    builder.setProgress(style.max, style.progress, style.indeterminate)
                }
            }
        }

        // 添加动作
        config.actions.forEach { action ->
            val actionPendingIntent =
                try {
                    PendingIntent.getActivity(
                        context,
                        action.hashCode(),
                        action.intent,
                        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                    )
                } catch (e: Exception) {
                    Log.e("NotificationUtils", "创建动作PendingIntent失败", e)
                    null
                }
            actionPendingIntent?.let { builder.addAction(action.icon, action.title, it) }
        }

        return builder
    }

    // ==================== 便捷方法 ====================

    /** 显示简单通知 */
    fun showSimpleNotification(
        id: Int,
        title: String,
        content: String,
        channelId: String = DEFAULT_CHANNEL_ID
    ): Boolean {
        return showNotification(
            NotificationConfig(id = id, channelId = channelId, title = title, content = content)
        )
    }

    /** 显示进度通知 */
    fun showProgressNotification(
        id: Int,
        title: String,
        content: String,
        max: Int,
        progress: Int,
        indeterminate: Boolean = false,
        channelId: String = DEFAULT_CHANNEL_ID
    ): Boolean {
        return showNotification(
            NotificationConfig(
                id = id,
                channelId = channelId,
                title = title,
                content = content,
                style = NotificationStyle.ProgressStyle(max, progress, indeterminate)
            )
        )
    }

    /** 显示大文本通知 */
    fun showBigTextNotification(
        id: Int,
        title: String,
        content: String,
        bigText: String,
        channelId: String = DEFAULT_CHANNEL_ID
    ): Boolean {
        return showNotification(
            NotificationConfig(
                id = id,
                channelId = channelId,
                title = title,
                content = content,
                style = NotificationStyle.BigTextStyle(bigText)
            )
        )
    }

    /** 显示大图片通知 */
    fun showBigPictureNotification(
        id: Int,
        title: String,
        content: String,
        bigPicture: Bitmap,
        bigLargeIcon: Bitmap? = null,
        channelId: String = DEFAULT_CHANNEL_ID
    ): Boolean {
        return showNotification(
            NotificationConfig(
                id = id,
                channelId = channelId,
                title = title,
                content = content,
                style = NotificationStyle.BigPictureStyle(bigPicture, bigLargeIcon)
            )
        )
    }

    // ==================== 通知管理 ====================

    /** 取消通知 */
    fun cancelNotification(id: Int): Boolean {
        return cancelNotification(Utils.getApp(), id)
    }

    /** 取消通知 */
    fun cancelNotification(context: Context, id: Int): Boolean {
        return try {
            val notificationManager = NotificationManagerCompat.from(context)
            notificationManager.cancel(id)
            Log.d(TAG, "取消通知成功: $id")
            true
        } catch (e: Exception) {
            Log.e(TAG, "取消通知失败: $id", e)
            false
        }
    }

    /** 取消所有通知 */
    fun cancelAllNotifications(): Boolean {
        return cancelAllNotifications(Utils.getApp())
    }

    /** 取消所有通知 */
    fun cancelAllNotifications(context: Context): Boolean {
        return try {
            val notificationManager = NotificationManagerCompat.from(context)
            notificationManager.cancelAll()
            Log.d(TAG, "取消所有通知成功")
            true
        } catch (e: Exception) {
            Log.e(TAG, "取消所有通知失败", e)
            false
        }
    }

    // ==================== 权限检查 ====================

    /** 检查通知是否启用 */
    fun areNotificationsEnabled(): Boolean {
        return areNotificationsEnabled(Utils.getApp())
    }

    /** 检查通知是否启用 */
    fun areNotificationsEnabled(context: Context): Boolean {
        return try {
            NotificationManagerCompat.from(context).areNotificationsEnabled()
        } catch (e: Exception) {
            Log.e(TAG, "检查通知权限失败", e)
            false
        }
    }

    /** 检查通知渠道是否启用 */
    fun isNotificationChannelEnabled(channelId: String): Boolean {
        return isNotificationChannelEnabled(Utils.getApp(), channelId)
    }

    /** 检查通知渠道是否启用 */
    fun isNotificationChannelEnabled(context: Context, channelId: String): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return true

        return try {
            val notificationManager =
                context.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
                    ?: return false
            val channel = notificationManager.getNotificationChannel(channelId)
            channel?.importance != NotificationManager.IMPORTANCE_NONE
        } catch (e: Exception) {
            Log.e(TAG, "检查通知渠道权限失败: $channelId", e)
            false
        }
    }

    // ==================== 工具方法 ====================

    /** 获取渠道名称 */
    private fun getChannelName(channelId: String): String {
        return when (channelId) {
            DEFAULT_CHANNEL_ID -> DEFAULT_CHANNEL_NAME
            "important" -> "重要通知"
            "normal" -> "普通通知"
            "silent" -> "静默通知"
            else -> "通知"
        }
    }

    /** 获取渠道重要性 */
    private fun getChannelImportance(priority: Int): Int {
        return when (priority) {
            NotificationCompat.PRIORITY_MIN -> NotificationManager.IMPORTANCE_MIN
            NotificationCompat.PRIORITY_LOW -> NotificationManager.IMPORTANCE_LOW
            NotificationCompat.PRIORITY_DEFAULT -> NotificationManager.IMPORTANCE_DEFAULT
            NotificationCompat.PRIORITY_HIGH -> NotificationManager.IMPORTANCE_HIGH
            NotificationCompat.PRIORITY_MAX -> NotificationManager.IMPORTANCE_MAX
            else -> NotificationManager.IMPORTANCE_DEFAULT
        }
    }

    /** 创建默认通知渠道 */
    fun createDefaultChannels(): Boolean {
        return try {
            createNotificationChannel(
                channelId = DEFAULT_CHANNEL_ID,
                channelName = DEFAULT_CHANNEL_NAME,
                importance = NotificationManager.IMPORTANCE_DEFAULT
            ) &&
                createNotificationChannel(
                    channelId = "important",
                    channelName = "重要通知",
                    importance = NotificationManager.IMPORTANCE_HIGH
                ) &&
                createNotificationChannel(
                    channelId = "normal",
                    channelName = "普通通知",
                    importance = NotificationManager.IMPORTANCE_DEFAULT
                ) &&
                createNotificationChannel(
                    channelId = "silent",
                    channelName = "静默通知",
                    importance = NotificationManager.IMPORTANCE_LOW
                )
        } catch (e: Exception) {
            Log.e(TAG, "创建默认通知渠道失败", e)
            false
        }
    }
}
