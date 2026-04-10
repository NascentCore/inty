package com.ai.imate.account.data.datasource

import android.content.Context
import com.ai.core.data.store.jsonDataStore
import com.ai.imate.account.data.bean.LoginResponse
import com.ai.imate.account.data.bean.UserProfile
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.map
import javax.inject.Inject

private val Context.account by jsonDataStore("account_data", LoginResponse("", UserProfile()))

class AuthLocalDataSource @Inject constructor(
    @param:ApplicationContext
    private val context: Context
) {
    val token = context.account.data.map { it.token }
    val userProfile = context.account.data.map { it.user }
    val isLogin = context.account.data.map { it.token.isNotBlank() }

    suspend fun updateAccount(loginResponse: LoginResponse) {
        context.account.updateData { loginResponse }
    }

    suspend fun clearAccount() {
        context.account.updateData { LoginResponse("", UserProfile()) }
    }
}