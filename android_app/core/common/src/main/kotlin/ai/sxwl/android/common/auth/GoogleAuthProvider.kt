package ai.sxwl.android.common.auth

import ai.sxwl.android.utils.LogUtils
import android.content.Context
import android.util.Base64
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.GetCredentialResponse
import androidx.credentials.exceptions.GetCredentialException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException

/**
 * Google登录提供者
 * 基于现代架构设计，提供Result-based API
 * 职责单一，专注于Google认证逻辑
 */
object GoogleAuthProvider {

    // 从Google Cloud Console获取的Web Client ID
    private const val WEB_CLIENT_ID =
        "1034291688895-0e5hq72pghd4nihhpmf989ptv0ag1542.apps.googleusercontent.com"

    /**
     * Google登录结果
     */
    sealed class GoogleLoginResult {
        data class Success(val loginData: ThirdAuth) : GoogleLoginResult()
        data class Error(val message: String, val exception: Throwable? = null) :
            GoogleLoginResult()
    }

    /**
     * 执行Google登录
     * @param context Android Context
     * @return GoogleLoginResult 包含登录结果
     */
    suspend fun signIn(context: Context): GoogleLoginResult {
        return signInWithConfig(context, showAddAccount = true)
    }

    /**
     * 执行Google登录（支持自定义配置）
     * @param context Android Context
     * @param showAddAccount 是否显示"添加账号"选项
     * @return GoogleLoginResult 包含登录结果
     */
    suspend fun signInWithConfig(
        context: Context,
        showAddAccount: Boolean = true
    ): GoogleLoginResult {
        return try {
            LogUtils.d("开始Google登录，showAddAccount=$showAddAccount")

            // 创建CredentialManager
            val credentialManager = CredentialManager.create(context)

            // 根据showAddAccount参数选择不同的登录方式
            val request = if (showAddAccount) {
                // 使用GetSignInWithGoogleOption，自动显示"添加账号"选项
                LogUtils.d("使用GetSignInWithGoogleOption进行登录")
                createSignInWithGoogleRequest()
            } else {
                // 使用GetGoogleIdOption，可控制是否显示"添加账号"选项
                LogUtils.d("使用GetGoogleIdOption进行登录")
                createGoogleIdOptionRequest(showAddAccount)
            }

            // 执行登录请求
            val response = credentialManager.getCredential(
                context = context,
                request = request
            )

            // 处理登录响应
            processCredentialResponse(response)

        } catch (e: GetCredentialException) {
            handleCredentialException(e)
        } catch (e: Exception) {
            LogUtils.e("Google登录异常", e)
            GoogleLoginResult.Error("登录过程中发生异常: ${e.message}", e)
        }
    }

    /**
     * 创建GetSignInWithGoogleOption请求（推荐方式）
     */
    private fun createSignInWithGoogleRequest(): GetCredentialRequest {
        val signInWithGoogleOption = GetSignInWithGoogleOption.Builder(
            serverClientId = WEB_CLIENT_ID
        ).build()

        return GetCredentialRequest.Builder()
            .addCredentialOption(signInWithGoogleOption)
            .build()
    }

    /**
     * 创建GetGoogleIdOption请求（传统方式）
     */
    private fun createGoogleIdOptionRequest(showAddAccount: Boolean): GetCredentialRequest {
        val googleIdOption = GetGoogleIdOption.Builder()
            .setFilterByAuthorizedAccounts(false) // 允许用户选择账户
            .setServerClientId(WEB_CLIENT_ID)
            .setAutoSelectEnabled(false) // 显示账户选择器
            .setRequestVerifiedPhoneNumber(showAddAccount) // 请求验证手机号，这会显示"添加账号"选项
            .build()

        return GetCredentialRequest.Builder()
            .addCredentialOption(googleIdOption)
            .build()
    }

    /**
     * 处理凭据响应
     */
    private fun processCredentialResponse(response: GetCredentialResponse): GoogleLoginResult {
        val credential = response.credential

        return when (credential) {
            is GoogleIdTokenCredential -> {
                processGoogleIdTokenCredential(credential)
            }

            is CustomCredential -> {
                processCustomCredential(credential)
            }

            else -> {
                LogUtils.e("不支持的凭据类型: ${credential.type}")
                GoogleLoginResult.Error("不支持的凭据类型: ${credential.type}")
            }
        }
    }

    /**
     * 处理GoogleIdTokenCredential
     */
    private fun processGoogleIdTokenCredential(credential: GoogleIdTokenCredential): GoogleLoginResult {
        return try {
            LogUtils.d("处理GoogleIdTokenCredential")

            val loginData = extractUserDataFromCredential(
                userId = credential.id,
                displayName = credential.displayName,
                idToken = credential.idToken,
                profilePictureUri = credential.profilePictureUri?.toString(),
                phoneNumber = credential.phoneNumber
            )

            LogUtils.d("Google登录成功: ${loginData.displayName} (${loginData.email})")
            GoogleLoginResult.Success(loginData)

        } catch (e: GoogleIdTokenParsingException) {
            LogUtils.e("Google ID Token解析失败", e)
            GoogleLoginResult.Error("Token解析失败", e)
        } catch (e: Exception) {
            LogUtils.e("处理Google凭据异常", e)
            GoogleLoginResult.Error("凭据处理失败", e)
        }
    }

    /**
     * 处理CustomCredential
     */
    private fun processCustomCredential(credential: CustomCredential): GoogleLoginResult {
        return try {
            if (credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
                LogUtils.d("处理Google自定义凭据")

                val googleCredential = GoogleIdTokenCredential.createFrom(credential.data)
                val loginData = extractUserDataFromCredential(
                    userId = googleCredential.id,
                    displayName = googleCredential.displayName,
                    idToken = googleCredential.idToken,
                    profilePictureUri = googleCredential.profilePictureUri?.toString(),
                    phoneNumber = googleCredential.phoneNumber
                )

                LogUtils.d("自定义凭据登录成功: ${loginData.displayName}")
                GoogleLoginResult.Success(loginData)

            } else {
                LogUtils.e("自定义凭据类型不匹配: ${credential.type}")
                GoogleLoginResult.Error("不支持的凭据类型: ${credential.type}")
            }
        } catch (e: Exception) {
            LogUtils.e("处理自定义凭据失败", e)
            GoogleLoginResult.Error("凭据处理失败: ${e.message}", e)
        }
    }

    /**
     * 从凭据中提取用户数据
     */
    private fun extractUserDataFromCredential(
        userId: String,
        displayName: String?,
        idToken: String,
        profilePictureUri: String?,
        phoneNumber: String?
    ): ThirdAuth {
        return ThirdAuth(
            id = userId,
            authToken = idToken,
            email = extractEmailFromToken(idToken),
            phoneNumber = phoneNumber,
            displayName = displayName ?: "Google用户",
            avatarUrl = profilePictureUri,
            provider = "Google",
            extraData = mapOf<String, String>(
                "email_verified" to "true",
                "provider" to "Google"
            )
        )
    }

    /**
     * 处理凭据异常
     */
    private fun handleCredentialException(e: GetCredentialException): GoogleLoginResult {
        LogUtils.e("Google凭据异常: ${e.javaClass.simpleName} - ${e.message}")

        return when (e) {
            is NoCredentialException -> {
                val message = """
                    没有可用的Google凭据，可能原因：
                    1. 设备上没有登录Google账户
                    2. Google Play Services版本过低
                    3. SHA-1指纹配置不匹配
                    4. Client ID配置错误
                    5. 网络连接问题
                """.trimIndent()

                LogUtils.d(message)
                GoogleLoginResult.Error("没有可用的Google账户，请检查设备设置", e)
            }

            else -> {
                LogUtils.e("Google登录失败", e)
                GoogleLoginResult.Error(e.message ?: "Google登录失败", e)
            }
        }
    }

    /**
     * 从JWT token中提取email
     */
    private fun extractEmailFromToken(idToken: String?): String? {
        return idToken?.let { token ->
            try {
                val parts = token.split(".")
                if (parts.size == 3) {
                    val payload = parts[1]
                    val decodedPayload = Base64.decode(payload, Base64.URL_SAFE)
                    val payloadJson = String(decodedPayload)

                    if (payloadJson.contains("\"email\":")) {
                        val emailMatch = "\"email\":\"([^\"]+)\"".toRegex().find(payloadJson)
                        emailMatch?.groupValues?.get(1)
                    } else null
                } else null
            } catch (e: Exception) {
                LogUtils.e("提取邮箱失败", e)
                null
            }
        }
    }
}
