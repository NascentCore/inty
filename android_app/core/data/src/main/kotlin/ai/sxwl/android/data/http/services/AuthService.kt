package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager

/** 认证服务 封装所有认证相关的API调用 替换原有的 IUserApi 认证相关方法 */
object AuthService {

    /** Google登录 替换: IUserApi.googleLogin() */
    suspend fun googleLogin(idToken: String): ApiResult<Pair<String, String>> {
        return IntyNetworkManager.executeRequest("Google Login") {
            val response =
                IntyNetworkManager.getClient()
                    .api()
                    .v1()
                    .auth()
                    .google()
                    .login(
                        com.inty.api.models.api.v1.auth.google.GoogleLoginParams.builder()
                            .idToken(idToken)
                            .build()
                    )

            val userId =
                response.data()?.user()?.id() ?: throw IllegalStateException("User ID is null")
            val token = response.data()?.token() ?: throw IllegalStateException("Token is null")

            Pair(userId, token)
        }
    }
}
