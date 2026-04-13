package com.inty.imate.account.data.datasource

import com.ai.core.http.utils.post
import com.inty.imate.account.data.bean.AccountDeletionResponse
import com.inty.imate.account.data.bean.LoginRequest
import com.inty.imate.account.data.bean.LoginResponse
import io.ktor.client.request.setBody
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

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

    suspend fun deleteAccount(): AccountDeletionResponse {
        return post<AccountDeletionResponse>("/api/v1/users/delete-account") {}
    }
}