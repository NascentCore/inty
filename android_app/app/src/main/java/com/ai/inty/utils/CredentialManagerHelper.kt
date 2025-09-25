package com.ai.inty.utils

import android.content.Context
import androidx.credentials.ClearCredentialStateRequest
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.GetCredentialResponse
import androidx.credentials.exceptions.GetCredentialException
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Credential Manager 助手类 使用最新的 Credential Manager API 进行 Google 登录 参考:
 * https://developer.android.google.cn/identity/sign-in/credential-manager-siwg?hl=zh-cn
 */
object CredentialManagerHelper {

    /**
     * 使用 Credential Manager & GetSignInWithGoogleOption 进行 Google 登录（支持现有账户和新用户注册）
     * https://developer.android.com/identity/sign-in/credential-manager
     */
    suspend fun signInWithGoogle(context: Context): Result<String> {
        return try {
            withContext(Dispatchers.Main) {
                // https://developer.android.com/identity/sign-in/credential-manager
                // Credential Manager 还提供了其他几种登录和注册方式：
                // 通行密钥 (Passkeys)：允许用户创建和使用密码的替代方案，提供更安全的登录体验。
                // 联合登录 (Federated sign-in)：通过 Google、Facebook 等身份提供商进行登录，简化了注册和登录流程。
                // 密码 (Password)：支持传统的用户名和密码登录方式。
                val credentialManager = CredentialManager.create(context)

                // 创建 Sign in with Google 选项
                // 注意：GetSignInWithGoogleOption 必须是 GetCredentialRequest 中的唯一选项
                // GetGoogleIdOption vs. GetSignInWithGoogleOption:
                // https://stackoverflow.com/a/78840062
                // GetGoogleIdOption 用于创建“使用 Google 账号登录”流程
                // GetSignInWithGoogleOption 用于触发“使用 Google 账号登录”按钮流程
                val signInWithGoogleOption =
                    GetSignInWithGoogleOption.Builder(
                            serverClientId = com.ai.inty.BuildConfig.WEB_CLIENT_ID
                        )
                        .build()

                // 创建获取凭证请求
                val request =
                    GetCredentialRequest.Builder()
                        .addCredentialOption(signInWithGoogleOption)
                        .build()

                // 获取凭证
                val response = credentialManager.getCredential(request = request, context = context)

                // 处理响应
                handleSignInWithGoogleResponse(response)
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
     * 根据官方文档：https://developer.android.google.cn/identity/sign-in/credential-manager-siwg?hl=zh-cn#trigger-siwg
     */
    private fun handleSignInWithGoogleResponse(response: GetCredentialResponse): Result<String> {
        return try {
            val credential = response.credential

            when (credential) {
                // 自定义凭证类型 (Google ID Token)
                is androidx.credentials.CustomCredential -> {
                    if (
                        credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
                    ) {
                        try {
                            // 使用 GoogleIdTokenCredential.createFrom 方法转换
                            val googleIdTokenCredential =
                                GoogleIdTokenCredential.createFrom(credential.data)
                            val idToken = googleIdTokenCredential.idToken
                            EasyLog.log("Google Sign-In successful via GetSignInWithGoogleOption")
                            Result.success(idToken)
                        } catch (e: GoogleIdTokenParsingException) {
                            EasyLog.log(
                                "Received an invalid google id token response",
                                EasyLog.ERROR,
                            )
                            Result.failure(Exception("Invalid Google ID token"))
                        }
                    } else {
                        EasyLog.log("Unexpected type of credential: ${credential.type}")
                        Result.failure(Exception("Unexpected credential type"))
                    }
                }

                else -> {
                    EasyLog.log(
                        "Unexpected type of credential: ${credential::class.java.simpleName}"
                    )
                    Result.failure(Exception("Unexpected credential type"))
                }
            }
        } catch (e: Exception) {
            EasyLog.log("Error handling credential response: ${e.message}", EasyLog.ERROR)
            Result.failure(e)
        }
    }

    /**
     * 清除凭证状态 当用户退出登录时调用 参考:
     * https://developer.android.com/identity/sign-in/credential-manager-siwg#handle-sign-out
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
