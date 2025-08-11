package com.ai.inty.utils

import android.content.Context
import androidx.credentials.ClearCredentialStateRequest
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.GetCredentialResponse
import androidx.credentials.exceptions.GetCredentialException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Credential Manager 助手类
 * 使用最新的 Credential Manager API 进行 Google 登录
 * 参考: https://developer.android.google.cn/identity/sign-in/credential-manager-siwg?hl=zh-cn
 */
object CredentialManagerHelper {

    /**
     * 使用 Credential Manager 进行 Google 登录
     */
    suspend fun signInWithGoogle(context: Context): Result<String> {
        return try {
            withContext(Dispatchers.Main) {
                val credentialManager = CredentialManager.create(context)

                // 创建 Google ID 选项
                val googleIdOption = GetGoogleIdOption.Builder()
                    .setFilterByAuthorizedAccounts(false)
                    .setServerClientId(com.ai.inty.BuildConfig.WEB_CLIENT_ID)
                    .build()

                // 创建获取凭证请求
                val request = GetCredentialRequest.Builder()
                    .addCredentialOption(googleIdOption)
                    .build()

                // 获取凭证
                val response = credentialManager.getCredential(
                    request = request,
                    context = context
                )

                // 处理响应
                handleCredentialResponse(response)
            }
        } catch (e: GetCredentialException) {
            EasyLog.log("Credential Manager sign-in failed: ${e.message}", EasyLog.ERROR)
            Result.failure(e)
        } catch (e: Exception) {
            EasyLog.log("Unexpected error during sign-in: ${e.message}", EasyLog.ERROR)
            Result.failure(e)
        }
    }

    /**
     * 处理凭证响应
     * 根据官方文档: https://developer.android.google.cn/identity/sign-in/credential-manager-siwg?hl=zh-cn
     */
    private fun handleCredentialResponse(response: GetCredentialResponse): Result<String> {
        return try {
            val credential = response.credential

            when (credential) {
                // Google ID Token 凭证
                is GoogleIdTokenCredential -> {
                    val idToken = credential.idToken
                    EasyLog.log("Google Sign-In successful via Credential Manager")
                    Result.success(idToken)
                }

                // 自定义凭证类型 (Google ID Token)
                is androidx.credentials.CustomCredential -> {
                    if (credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
                        try {
                            // 使用 GoogleIdTokenCredential.createFrom 方法转换
                            val googleIdTokenCredential =
                                GoogleIdTokenCredential.createFrom(credential.data)
                            val idToken = googleIdTokenCredential.idToken
                            EasyLog.log("Google Sign-In successful via CustomCredential")
//                            Log.w(
//                                "测试",
//                                "Email： ${googleIdTokenCredential.id} ,,Name： ${googleIdTokenCredential.displayName} ,, Avatar: ${googleIdTokenCredential.profilePictureUri} ",
//                            )

                            Result.success(idToken)
                        } catch (e: GoogleIdTokenParsingException) {
                            EasyLog.log(
                                "Received an invalid google id token response",
                                EasyLog.ERROR
                            )
                            Result.failure(Exception("Invalid Google ID token"))
                        }
                    } else {
                        EasyLog.log("Unexpected type of credential: ${credential.type}")
                        Result.failure(Exception("Unexpected credential type"))
                    }
                }

                else -> {
                    EasyLog.log("Unexpected type of credential: ${credential::class.java.simpleName}")
                    Result.failure(Exception("Unexpected credential type"))
                }
            }
        } catch (e: Exception) {
            EasyLog.log("Error handling credential response: ${e.message}", EasyLog.ERROR)
            Result.failure(e)
        }
    }

    /**
     * 检查是否支持 Credential Manager
     */
    fun isCredentialManagerSupported(context: Context): Boolean {
        return try {
            val credentialManager = CredentialManager.create(context)
            // 检查是否支持 Google ID 选项
            true
        } catch (e: Exception) {
            EasyLog.log("Credential Manager not supported: ${e.message}", EasyLog.ERROR)
            false
        }
    }

    /**
     * 获取错误消息
     */
    fun getErrorMessage(exception: GetCredentialException): String {
        return when (exception) {
            is NoCredentialException -> "没有可用的登录凭证"
            else -> "登录失败: ${exception.message}"
        }
    }

    /**
     * 清除凭证状态
     * 当用户退出登录时调用
     */
    suspend fun clearCredentialState(context: Context) {
        try {
            val credentialManager = CredentialManager.create(context)
            credentialManager.clearCredentialState(ClearCredentialStateRequest())
            EasyLog.log("Credential state cleared successfully")
        } catch (e: Exception) {
            EasyLog.log("Error clearing credential state: ${e.message}", EasyLog.ERROR)
        }
    }
} 