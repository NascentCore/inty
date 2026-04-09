package com.ai.imate.account.data

import com.ai.imate.account.data.datasource.AuthLocalDataSource
import com.ai.imate.account.data.datasource.AuthRemoteDataSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject

class AuthRepository @Inject constructor(
    private val authRemoteDataSource: AuthRemoteDataSource,
    private val authLocalDataSource: AuthLocalDataSource
) {

    val token = authLocalDataSource.token
    val isLogin = authLocalDataSource.isLogin

    suspend fun googleLogin(idToken: String) {

        withContext(Dispatchers.IO) {
            val response = authRemoteDataSource.googleLogin(idToken)

            authLocalDataSource.updateAccount(response)
        }
    }

    suspend fun emailLogin(email: String, password: String) {
        withContext(Dispatchers.IO) {
            val response = authRemoteDataSource.emailLogin(email, password)

            authLocalDataSource.updateAccount(response)
        }
    }
}