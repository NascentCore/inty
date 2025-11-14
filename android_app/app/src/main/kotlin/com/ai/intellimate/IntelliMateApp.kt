package com.ai.intellimate

import ai.sxwl.android.common.analytics.GlobalExceptionHandler
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.di.DataModule
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.services.UserService
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.firebase.DirectBootStorage
import ai.sxwl.android.firebase.DirectBootUtils
import ai.sxwl.android.firebase.FCMService
import ai.sxwl.android.firebase.FCMTokenUploadCallback
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.ai.intellimate.utils.AgentCacheProviderImpl
import com.ai.intellimate.utils.RecommendedAgentCacheProviderImpl
import com.ai.intellimate.utils.UnifiedStartupManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/** 应用Application的实现类 */
class IntelliMateApp : Application() {

    override fun onCreate() {
        super.onCreate()
        // 初始化网络管理器（IntyNetworkManager 内部已包含 NetworkStateManager）
        IntyNetworkManager.initialize(this, buildType = BuildConfig.BUILD_TYPE)

        // 初始化缓存提供者并注入到DataModule
        val chatCacheProvider = AgentCacheProviderImpl()
        val recommendedCacheProvider = RecommendedAgentCacheProviderImpl()
        DataModule.setAgentCacheProvider(chatCacheProvider)
        DataModule.setRecommendedCacheProvider(recommendedCacheProvider)
        LogUtils.i("IntelliMateApp - 数据层依赖注入初始化完成")

        // 立即初始化统一启动管理器（只做必要的登录判断，不阻塞）
        UnifiedStartupManager.initializeEssential(this)

        // Firebase初始化和设备信息设置
        initializeFirebaseAnalytics()

        // 初始化 Remote Config 并设置聊天开关的默认值
        initializeRemoteConfigDefaults()

        // 设置FCM token上传回调（连接infrastructure层和data层）
        setupFCMTokenUploadCallback()

        // 处理 Direct Boot 模式下保存的消息（用户解锁后）
        handleDirectBootPendingMessages()

        // 安装全局异常处理器
        GlobalExceptionHandler.install(this)

        // 异步初始化所有可能阻塞的组件
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // 异步进行完整的数据预加载和缓存
                UnifiedStartupManager.initializeAsync(this@IntelliMateApp)
            } catch (e: Exception) {
                LogUtils.e("IntyApp - 异步初始化失败: ${e.message}")
            }
        }
    }

    /** Firebase Analytics初始化 */
    private fun initializeFirebaseAnalytics() {
        // FirebaseManager内部已有完善的异常处理，这里主要是Application级别的额外保护
        // FirebaseInitializer已经自动初始化了FirebaseManager，这里作为备用保障

        // 记录应用启动事件 - 使用Firebase内置事件
        FirebaseManager.logEvent(FirebaseManager.Events.APP_OPEN)

        // 设置设备信息
        FirebaseManager.setDeviceInfo()

        LogUtils.i("IntelliMateApp - Firebase Analytics初始化完成")
    }

    /**
     * 初始化 Remote Config 默认值并获取配置
     * 用于设置聊天开关的默认值（Keep Talking 和 Auto Play Voice）
     */
    private fun initializeRemoteConfigDefaults() {
        // 异步初始化，避免阻塞应用启动
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // 设置 Remote Config 默认值（降级方案）
                // 如果 Firebase 后台未配置或网络不可用，使用这些默认值
                FirebaseManager.setRemoteConfigDefaults(
                    mapOf(
                        // Keep Talking 开关默认值（false = 关闭）
                        FirebaseManager.RemoteConfigKeys.AUTO_ENABLE_KEEP_TALKING to false,
                        // Auto Play Opening Voice 开关默认值（true = 开启）
                        FirebaseManager.RemoteConfigKeys.AUTO_PLAY_OPENING_VOICE to true,
                    )
                )

                // 获取并激活 Remote Config
                val hasNewConfig = FirebaseManager.fetchAndActivateRemoteConfig()
                if (hasNewConfig) {
                    LogUtils.i("IntelliMateApp", "Remote Config 已获取并激活新配置")
                }

                // 在调试模式下输出所有 Remote Config 参数（用于验证配置）
                if (ai.sxwl.android.utils.AppUtils.isAppDebug()) {
                    val allConfig = FirebaseManager.getAllRemoteConfigValues()
                    if (allConfig.isNotEmpty()) {
                        LogUtils.d(
                            "IntelliMateApp",
                            "Remote Config 所有参数: ${allConfig.entries.joinToString { "${it.key}=${it.value}" }}"
                        )
                    }
                }

                // 从 Remote Config 读取默认值并初始化设置
                SettingStateManager.initializeFromRemoteConfig()
            } catch (e: Exception) {
                LogUtils.e("IntelliMateApp", "初始化 Remote Config 失败: ${e.message}", e)
                // 即使 Remote Config 失败，也使用本地默认值初始化
                SettingStateManager.initializeFromRemoteConfig()
            }
        }
    }

    /**
     * Setup FCM token upload callback
     *
     * Connects infrastructure layer (core/firebase) with data layer (core/data)
     * This avoids circular dependency between modules
     */
    private fun setupFCMTokenUploadCallback() {
        FirebaseManager.setTokenUploadCallback(object : FCMTokenUploadCallback {
            override suspend fun uploadToken(token: String) {
                // Check if user is logged in before uploading token
                // This avoids 401 errors when token is obtained before login
                if (!ai.sxwl.android.data.store.IntySetting.isLogin() ||
                    ai.sxwl.android.data.store.IntySetting.getCurToken().isEmpty()
                ) {
                    LogUtils.w("IntelliMateApp", "用户未登录，跳过 FCM Token 上传。登录后将自动上传。")
                    return
                }

                // Delegate to UserService in data layer
                when (val result = UserService.registerDeviceToken(token)) {
                    is ai.sxwl.android.data.http.ApiResult.Success -> {
                        LogUtils.i("IntelliMateApp", "FCM Token 上传成功")
                    }

                    is ai.sxwl.android.data.http.ApiResult.Error -> {
                        LogUtils.e("IntelliMateApp", "FCM Token 上传失败: ${result.message}")
                    }
                }
            }
        })
        LogUtils.d("IntelliMateApp", "FCM Token 上传回调已设置")
    }

    /**
     * 处理 Direct Boot 模式下保存的待处理消息
     * 在用户解锁后（应用启动时）调用，处理在 Direct Boot 模式下接收到的消息
     */
    private fun handleDirectBootPendingMessages() {
        // 检查用户是否已解锁
        if (!DirectBootUtils.isUserUnlocked(this)) {
            LogUtils.d("IntelliMateApp", "用户未解锁，跳过处理 Direct Boot 待处理消息")
            return
        }

        // 异步处理，避免阻塞应用启动
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // 初始化 Direct Boot 存储（用户已解锁，可以访问）
                DirectBootStorage.initialize(this@IntelliMateApp)

                // 调试：打印存储状态（仅在调试模式下）
                if (ai.sxwl.android.utils.AppUtils.isAppDebug()) {
                    DirectBootStorage.debugPrintStatus(this@IntelliMateApp)
                }

                // 获取待处理的消息
                val pendingMessages = DirectBootStorage.getPendingMessages(this@IntelliMateApp)
                val messageCount = pendingMessages.size

                if (messageCount > 0) {
                    LogUtils.i(
                        "IntelliMateApp",
                        "发现 $messageCount 条 Direct Boot 模式下保存的待处理消息，开始处理"
                    )

                    // 处理每条消息
                    pendingMessages.forEach { message ->
                        try {
                            handlePendingMessage(message)
                        } catch (e: Exception) {
                            LogUtils.e(
                                "IntelliMateApp",
                                "处理待处理消息失败: messageId=${message.messageId}",
                                e
                            )
                        }
                    }

                    // 清除已处理的消息
                    DirectBootStorage.clearPendingMessages(this@IntelliMateApp)
                    LogUtils.i("IntelliMateApp", "Direct Boot 待处理消息处理完成，已清除")
                } else {
                    LogUtils.d("IntelliMateApp", "没有 Direct Boot 待处理消息")
                }
            } catch (e: Exception) {
                LogUtils.e("IntelliMateApp", "处理 Direct Boot 待处理消息失败", e)
            }
        }
    }

    /**
     * 处理单条待处理消息
     * 根据消息类型显示通知或执行相应操作
     */
    private fun handlePendingMessage(message: DirectBootStorage.PendingMessage) {
        // 如果有标题和内容，显示通知
        if (!message.title.isNullOrEmpty() && !message.body.isNullOrEmpty()) {
            showNotificationForPendingMessage(message)
        } else {
            LogUtils.d(
                "IntelliMateApp",
                "待处理消息缺少标题或内容，跳过显示通知: messageId=${message.messageId}"
            )
        }
    }

    /**
     * 为待处理消息显示通知
     */
    private fun showNotificationForPendingMessage(message: DirectBootStorage.PendingMessage) {
        try {
            // 确保通知渠道已创建
            createNotificationChannelIfNeeded()

            // 构建通知数据
            val data = mutableMapOf<String, String>()
            message.type?.let { data["type"] = it }
            message.agentId?.let { data["agent_id"] = it }

            // 构建通知
            val builder = NotificationCompat.Builder(this, FCMService.NOTIFICATION_CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(message.title)
                .setContentText(message.body)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setAutoCancel(true)
                .setDefaults(NotificationCompat.DEFAULT_ALL)
                .setWhen(message.timestamp)

            // 根据消息类型设置点击跳转（简化实现，直接跳转到主页面）
            // 实际项目中可以根据 message.type 和 message.agentId 进行更精确的跳转
            val intent = packageManager.getLaunchIntentForPackage(packageName)?.apply {
                flags =
                    android.content.Intent.FLAG_ACTIVITY_NEW_TASK or android.content.Intent.FLAG_ACTIVITY_CLEAR_TOP
            }

            if (intent != null) {
                val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    android.app.PendingIntent.FLAG_IMMUTABLE or android.app.PendingIntent.FLAG_UPDATE_CURRENT
                } else {
                    android.app.PendingIntent.FLAG_UPDATE_CURRENT
                }
                val pendingIntent = android.app.PendingIntent.getActivity(this, 0, intent, flags)
                builder.setContentIntent(pendingIntent)
            }

            // 显示通知
            val notificationManager = NotificationManagerCompat.from(this)
            if (notificationManager.areNotificationsEnabled()) {
                val notificationId = message.messageId.hashCode()
                notificationManager.notify(notificationId, builder.build())
                LogUtils.d(
                    "IntelliMateApp",
                    "已为待处理消息显示通知: messageId=${message.messageId}, title=${message.title}"
                )
            } else {
                LogUtils.w("IntelliMateApp", "通知权限未授予，无法显示待处理消息通知")
            }
        } catch (e: Exception) {
            LogUtils.e("IntelliMateApp", "显示待处理消息通知失败", e)
        }
    }

    /**
     * 创建通知渠道（Android 8.0+ 必需）
     */
    private fun createNotificationChannelIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val notificationManager = getSystemService(NotificationManager::class.java)

            if (notificationManager.getNotificationChannel(FCMService.NOTIFICATION_CHANNEL_ID) == null) {
                val channel = NotificationChannel(
                    FCMService.NOTIFICATION_CHANNEL_ID,
                    "Push Notifications",
                    NotificationManager.IMPORTANCE_DEFAULT
                ).apply {
                    description = "Receive push notifications and messages"
                    enableVibration(true)
                    vibrationPattern = longArrayOf(0, 250, 250, 250)
                    enableLights(true)
                }

                notificationManager.createNotificationChannel(channel)
            }
        }
    }

    override fun onTerminate() {
        super.onTerminate()
        // 应用退出时释放Billing连接
        if (BillingRepository.isInitialized()) {
            LogUtils.i("IntyApp - 应用退出，释放Billing连接")
            BillingRepository.release()
        }
    }
}
