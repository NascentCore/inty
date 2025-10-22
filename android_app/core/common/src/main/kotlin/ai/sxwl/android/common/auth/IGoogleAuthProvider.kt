package ai.sxwl.android.common.auth

import android.content.Context
import kotlinx.serialization.Serializable

/**
 * Google登录提供者接口
 * 统一真实和模拟Google登录的接口
 */
interface IGoogleAuthProvider {

    /**
     * 执行Google登录
     * @param context Android Context
     * @return GoogleLoginResult 包含登录结果
     */
    suspend fun signIn(context: Context): GoogleLoginResult

    /**
     * 执行Google登录（支持自定义配置）
     * @param context Android Context
     * @param showAddAccount 是否显示"添加账号"选项
     * @return GoogleLoginResult 包含登录结果
     */
    suspend fun signInWithConfig(context: Context, showAddAccount: Boolean): GoogleLoginResult

    /**
     * Google登录结果
     */
    sealed class GoogleLoginResult {
        data class Success(val loginData: ThirdAuth) : GoogleLoginResult()
        data class Error(val message: String, val exception: Throwable? = null) :
            GoogleLoginResult()
    }
}

/**
 * 真实Google登录提供者包装器
 */
class RealGoogleAuthProviderWrapper : IGoogleAuthProvider {

    override suspend fun signIn(context: Context): IGoogleAuthProvider.GoogleLoginResult {
        return when (val result = GoogleAuthProvider.signIn(context)) {
            is GoogleAuthProvider.GoogleLoginResult.Success -> {
                IGoogleAuthProvider.GoogleLoginResult.Success(result.loginData)
            }

            is GoogleAuthProvider.GoogleLoginResult.Error -> {
                IGoogleAuthProvider.GoogleLoginResult.Error(result.message, result.exception)
            }
        }
    }

    override suspend fun signInWithConfig(
        context: Context,
        showAddAccount: Boolean
    ): IGoogleAuthProvider.GoogleLoginResult {
        return when (val result = GoogleAuthProvider.signInWithConfig(context, showAddAccount)) {
            is GoogleAuthProvider.GoogleLoginResult.Success -> {
                IGoogleAuthProvider.GoogleLoginResult.Success(result.loginData)
            }

            is GoogleAuthProvider.GoogleLoginResult.Error -> {
                IGoogleAuthProvider.GoogleLoginResult.Error(result.message, result.exception)
            }
        }
    }
}

/**
 * 调用第三方sdk获取授权信息的返回数据类
 */
@Serializable
data class ThirdAuth(
    val id: String? = null,//第三方授权返回的用户id
    val authToken: String? = null,//sdk的授权idToken
    val email: String? = null,//邮箱
    val displayName: String? = null,//昵称，或者用于展示的名字
    val avatarUrl: String? = null,//头像url
    val phoneNumber: String? = null,//手机号
    val provider: String = "Google",//第三方平台标记
    val extraData: Map<String, String>? = emptyMap(),//额外数据
)
