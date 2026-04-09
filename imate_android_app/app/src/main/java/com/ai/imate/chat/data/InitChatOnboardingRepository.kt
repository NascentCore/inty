package com.ai.imate.chat.data

import com.ai.imate.chat.data.datasource.InitChatOnboardingLocalDataSource
import com.ai.imate.chat.data.datasource.InitChatRemoteDataSource
import com.ai.imate.chat.data.bean.GenerateAvatarResponse
import com.ai.imate.chat.data.bean.InitChatOnboarding
import com.ai.imate.chat.data.bean.InitChatOnboardingGender
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow

class InitChatOnboardingRepository @Inject constructor(
    private val localDataSource: InitChatOnboardingLocalDataSource,
    private val remoteDataSource: InitChatRemoteDataSource,
) {
    val onboarding: Flow<InitChatOnboarding> = localDataSource.onboarding

    val onboardingCompleted: Flow<Boolean> = localDataSource.onboardingCompleted

    val nickname: Flow<String?> = localDataSource.nickname

    val gender: Flow<InitChatOnboardingGender?> = localDataSource.gender

    val avatarUrl: Flow<String?> = localDataSource.avatarUrl

    suspend fun isOnboardingCompleted(): Boolean = localDataSource.isOnboardingCompleted()

    suspend fun setOnboardingCompleted(completed: Boolean) {
        localDataSource.setOnboardingCompleted(completed)
    }

    suspend fun setNickname(nickname: String) {
        localDataSource.setNickname(nickname)
    }

    suspend fun setGender(gender: InitChatOnboardingGender) {
        localDataSource.setGender(gender)
    }

    suspend fun setAvatarUrl(avatarUrl: String) {
        localDataSource.setAvatarUrl(avatarUrl)
    }

    suspend fun generateAvatar(prompt: String): GenerateAvatarResponse =
        remoteDataSource.generateAvatar(prompt)
}
