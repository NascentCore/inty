package com.ai.imate.account.data.datasource

import com.ai.imate.account.data.bean.LoginRequest
import com.ai.imate.account.data.bean.LoginResponse
import io.ktor.client.request.setBody
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import com.ai.core.http.utils.post

class AuthRemoteDataSource @Inject constructor() {
    /**
     * Google登录
     */
    suspend fun googleLogin(idToken: String): LoginResponse {
        return post<LoginResponse>("/api/v1/auth/google/login") {
            setBody(LoginRequest(idToken))
        }
    }

    suspend fun emailLogin(email: String, password: String): LoginResponse {
        return post<LoginResponse>("/api/v1/auth/google/login") {
            setBody(LoginRequest(email = email, password = password))
        }
    }
}