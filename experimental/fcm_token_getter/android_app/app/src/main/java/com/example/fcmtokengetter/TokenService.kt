package com.example.fcmtokengetter

import android.util.Log
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.tasks.await
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.logging.HttpLoggingInterceptor
import org.json.JSONObject

class TokenService {
    private val client: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .addInterceptor(HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            })
            .build()
    }

    /**
     * 获取 FCM token
     */
    suspend fun getFCMToken(): String? {
        return try {
            val token = FirebaseMessaging.getInstance().token.await()
            Log.i(TAG, "FCM Token 获取成功: $token")
            token
        } catch (e: Exception) {
            Log.e(TAG, "获取 FCM Token 失败", e)
            null
        }
    }

    /**
     * 将 token 注册到服务器
     *
     * @param token FCM token
     * @param authToken 用户认证 token (Bearer token)
     * @param baseUrl 后端 API 基础地址
     * @return 注册结果，成功返回 true，失败返回 false 并记录错误日志
     */
    suspend fun registerTokenToServer(
        token: String,
        authToken: String,
        baseUrl: String = ServerConfig.BASE_URL
    ): RegisterResult {
        return try {
            val url = "$baseUrl${ServerConfig.REGISTER_DEVICE_TOKEN_PATH}"
            val body = JSONObject()
                .put("token", token)
                .toString()
                .toRequestBody("application/json".toMediaType())

            val request = Request.Builder()
                .url(url)
                .post(body)
                .addHeader("Authorization", "Bearer $authToken")
                .addHeader("Content-Type", "application/json")
                .build()

            val response = client.newCall(request).execute()
            val responseBody = response.body?.string()

            if (response.isSuccessful) {
                Log.i(TAG, "Token 注册成功: $responseBody")
                RegisterResult.Success("Token 注册成功")
            } else {
                val errorMsg = "注册失败: ${response.code} - $responseBody"
                Log.e(TAG, errorMsg)
                RegisterResult.Error(errorMsg)
            }
        } catch (e: Exception) {
            val errorMsg = "注册失败: ${e.message}"
            Log.e(TAG, errorMsg, e)
            RegisterResult.Error(errorMsg)
        }
    }

    sealed class RegisterResult {
        data class Success(val message: String) : RegisterResult()
        data class Error(val message: String) : RegisterResult()
    }

    companion object {
        private const val TAG = "TokenService"
    }
}


