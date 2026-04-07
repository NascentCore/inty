package com.ai.imate.account.data.bean

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class UserProfile(
    @SerialName("age_group") val ageGroup: String? = null,
    @SerialName("auth_type") val authType: String = "",
    val avatar: String? = null,
    @SerialName("user_photo") val userPhoto: String? = null,
    @SerialName("created_at") val createdAt: String = "",
    // description 是早期的称为，目前其在 App 中被称作 persona
    // Persona 指的是AI 角色看到的人类用户的“角色设定”
    val description: String? = null,
    val email: String? = null,
    val gender: String? = null,
    val id: String = "",
    @SerialName("readable_id") val readableId: String = "",
    @SerialName("is_active") val isActive: Boolean = false,
    @SerialName("is_superuser") val isSuperuser: Boolean = false,
    val nickname: String = "",
    val phone: String? = null,
    @SerialName("system_language") val systemLanguage: String = "",
    @SerialName("updated_at") val updatedAt: String? = null,
    @SerialName("public_agents_count") val publicAgentsCount: Int = 0,
    @SerialName("total_public_agents_follows") val totalAgentsFollows: Int = 0,
    @SerialName("followers_count") val followerCount: Int = 0,
    @SerialName("connector_count") val connectorCount: Int = 0,
)