package com.ai.inty.netapi.services

import com.ai.inty.netapi.ApiResult
import com.ai.inty.netapi.IntyNetworkManager

import com.inty.api.models.api.v1.auth.AuthCreateGuestParams
import com.inty.utils.AppEnv

/**
 * 认证服务
 * 封装所有认证相关的API调用
 * 替换原有的 IUserApi 认证相关方法
 */
object AuthService {

    /**
     * 创建游客账户
     * 替换: IUserApi.createGuest()
     */
    suspend fun createGuest(): ApiResult<Pair<String, String>> {
        return IntyNetworkManager.executeRequest("Create Guest") {
            val response = IntyNetworkManager.getClient()
                .api().v1().auth().createGuest(
                    AuthCreateGuestParams.builder()
                        .deviceId(AppEnv.DeviceID)
                        .systemLanguage(AppEnv.locale.language)
                        .build()
                )

            val guestId = response.data()?.guestId()
                ?: throw IllegalStateException("Guest ID is null")
            val token = response.data()?.token()
                ?: throw IllegalStateException("Token is null")

            Pair(guestId, token)
        }
    }

    /**
     * Google登录
     * 替换: IUserApi.googleLogin()
     */
    suspend fun googleLogin(idToken: String): ApiResult<Pair<String, String>> {
        return IntyNetworkManager.executeRequest("Google Login") {
            val response = IntyNetworkManager.getClient()
                .api().v1().auth().google().login(
                    com.inty.api.models.api.v1.auth.google.GoogleLoginParams.builder()
                        .idToken(idToken)
                        .build()
                )

            val userId = response.data()?.user()?.id()
                ?: throw IllegalStateException("User ID is null")
            val token = response.data()?.token()
                ?: throw IllegalStateException("Token is null")

            Pair(userId, token)
        }
    }

    /**
     * 刷新Token
     * 替换: IUserApi.refreshToken()
     * 注意: 当前 IntySDK 没有直接的 refresh API，通过重新登录实现
     */
    suspend fun refreshToken(): ApiResult<String> {
        return IntyNetworkManager.executeRequest("Refresh Token") {
            // 当前 IntySDK 没有 refresh token API
            // 可以通过重新验证用户身份来获取新 token
            // 这里暂时抛出异常，提示需要重新登录
            throw Exception("Refresh token not supported, please re-login")
        }
    }

    /**
     * 登出
     * 替换: IUserApi.logout()
     * 注意: IntySDK可能没有直接的logout API，需要根据实际情况实现
     */
    suspend fun logout(): ApiResult<Unit> {
        return IntyNetworkManager.executeRequest("Logout") {
            // 这里需要根据实际的IntySDK API来实现
            // 目前先清除客户端缓存
            IntyNetworkManager.clearClientCache()
        }
    }

    /**
     * 验证Token有效性
     * 替换: IUserApi.validateToken()
     * 注意: IntySDK可能没有直接的validate API，可以通过获取用户信息来验证
     */
    suspend fun validateToken(): ApiResult<Boolean> {
        return IntyNetworkManager.executeRequest("Validate Token") {
            // 通过获取用户信息来验证token有效性
            try {
                val response = IntyNetworkManager.getClient()
                    .api().v1().users().profile().retrieve()
                response.code() == 200L
            } catch (e: Exception) {
                false
            }
        }
    }
}
