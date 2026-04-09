package com.ai.imate.chat.data.datasource

import android.content.Context
import com.ai.core.data.store.jsonDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import com.ai.imate.chat.data.bean.InitChatOnboarding
import com.ai.imate.chat.data.bean.InitChatOnboardingGender
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.initChatOnboardingStore by jsonDataStore(
    fileName = "init_chat_onboarding",
    defaultValue = InitChatOnboarding(),
)

class InitChatOnboardingLocalDataSource @Inject constructor(
    @param:ApplicationContext private val context: Context,
) {
    val onboarding: Flow<InitChatOnboarding> = context.initChatOnboardingStore.data

    val onboardingCompleted: Flow<Boolean> = onboarding.map { it.completed }

    val nickname: Flow<String?> = onboarding.map { it.nickname }

    val gender: Flow<InitChatOnboardingGender?> = onboarding.map { it.gender }

    val avatarUrl: Flow<String?> = onboarding.map { it.avatarUrl }

    suspend fun isOnboardingCompleted(): Boolean =
        context.initChatOnboardingStore.data.first().completed

    suspend fun setOnboardingCompleted(completed: Boolean) {
        context.initChatOnboardingStore.updateData { it.copy(completed = completed) }
    }

    suspend fun setNickname(nickname: String) {
        context.initChatOnboardingStore.updateData { it.copy(nickname = nickname) }
    }

    suspend fun setGender(gender: InitChatOnboardingGender) {
        context.initChatOnboardingStore.updateData { it.copy(gender = gender) }
    }

    suspend fun setAvatarUrl(avatarUrl: String) {
        context.initChatOnboardingStore.updateData { it.copy(avatarUrl = avatarUrl) }
    }
}
