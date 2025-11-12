package com.example.fcmserverpush

import android.util.Log
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor

class ServerPushMessagingService : FirebaseMessagingService() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private val client: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .addInterceptor(HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            })
            .build()
    }

    private val fetcher by lazy { ResultFetcher(client) }

    // 在前台接收数据消息的回调详见: https://firebase.google.com/docs/cloud-messaging/android/receive?hl=zh-cn#override
    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        val jobId = message.data["job_id"]
        if (jobId.isNullOrBlank()) {
            Log.w(TAG, "收到的推送缺少 job_id")
            return
        }

        scope.launch {
            runCatching {
                val result = fetcher.fetch(jobId)
                JobResultBus.emit(result)
                Log.i(TAG, "已获取结果 jobId=$jobId")
            }.onFailure { error ->
                Log.e(TAG, "获取结果失败 jobId=$jobId", error)
            }
        }
    }

    // 监听令牌刷新流程详见: https://firebase.google.com/docs/cloud-messaging/android/client?hl=zh-cn#monitor-token
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.i(TAG, "FCM token 刷新: $token")
    }

    companion object {
        private const val TAG = "ServerPushService"
    }
}
