package com.inty.imate.chat.data.bean

import kotlinx.serialization.Serializable

@Serializable
enum class InitChatOnboardingGender {
    Male,
    Female,
    NoPref,
}

@Serializable
data class InitChatOnboarding(
    val nickname: String? = null,
    val gender: InitChatOnboardingGender? = null,
    val avatarUrl: String? = null,
    val createdAgent: AgentInfo? = null,
)

