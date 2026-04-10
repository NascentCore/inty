package com.ai.imate.account.data

import com.ai.imate.account.AuthPostLoginNavigationGate
import com.ai.imate.account.data.datasource.AuthLocalDataSource
import com.ai.imate.account.data.datasource.AuthRemoteDataSource
import com.ai.imate.chat.data.datasource.ChatLocalDataSource
import com.ai.imate.chat.data.datasource.InitChatOnboardingLocalDataSource
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class AuthRepository
@Inject
constructor(
    private val authRemoteDataSource: AuthRemoteDataSource,
    private val authLocalDataSource: AuthLocalDataSource,
    private val initChatOnboardingLocalDataSource: InitChatOnboardingLocalDataSource,
    private val chatLocalDataSource: ChatLocalDataSource,
    private val authPostLoginNavigationGate: AuthPostLoginNavigationGate,
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

    suspend fun logout() {
        withContext(Dispatchers.IO) {
            authLocalDataSource.clearAccount()
            authPostLoginNavigationGate.releaseHold()
        }
    }

    suspend fun deleteAccount() {
        withContext(Dispatchers.IO) {
            authRemoteDataSource.deleteAccount()
            authLocalDataSource.clearAccount()
            initChatOnboardingLocalDataSource.resetOnboarding()
            chatLocalDataSource.clearAllMessages()
            authPostLoginNavigationGate.releaseHold()
        }
    }
}