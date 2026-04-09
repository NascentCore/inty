package com.ai.imate.chat.data.bean

import kotlinx.serialization.Serializable

@Serializable
enum class InitChatOnboardingGender {
    Male,
    Female,
    NoPref,
}

@Serializable
data class InitChatOnboarding(
    val completed: Boolean = false,
    val nickname: String? = null,
    val gender: InitChatOnboardingGender? = null,
    val avatarUrl: String? = null,
)

