package com.ai.inty.beans

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class CreateGuestReq(
    val device_id: String,
    val system_language: String
)

@JsonClass(generateAdapter = true)
data class CreateGuestResult(
    val guest_id: String,
    val token: String,
    val is_new_guest: Boolean,
)

@JsonClass(generateAdapter = true)
data class UserProfile(
    @Json(name = "age_group")
    val ageGroup: Any? = null,
    @Json(name = "auth_type")
    val authType: String = "",
    val avatar: String? = null,
    @Json(name = "created_at")
    val createdAt: String = "",
    val description: String? = null,
    val email: String? = null,
    val gender: String? = null,
    val id: String = "",
    @Json(name = "readable_id")
    val readableId: String = "",
    @Json(name = "is_active")
    val isActive: Boolean = false,
    @Json(name = "is_superuser")
    val isSuperuser: Boolean = false,
    val nickname: String = "",
    val phone: String? = null,
    @Json(name = "system_language")
    val systemLanguage: String = "",
    @Json(name = "updated_at")
    val updatedAt: String? = null
)

enum class GENDER(val value: String) {
    MALE("MALE"),
    FEMALE("FEMALE"),
    OTHER("OTHER"),
}

@JsonClass(generateAdapter = true)
data class TokenBean(
    val token: String
)

@JsonClass(generateAdapter = true)
data class GoogleLoginRequest(
    @Json(name = "id_token")
    val idToken: String
)

@JsonClass(generateAdapter = true)
data class GoogleLoginResponse(
    val token: String,
    val user: UserProfile
)

/**
 * 检查账号删除的接口返回
 */
@JsonClass(generateAdapter = true)
data class UserDeletionCheckResponse(
    val active_subscription: Boolean,
    val can_delete: Boolean,
    val error_message: String?
)

/**
 * 删除账号的结果返回
 */
@JsonClass(generateAdapter = true)
data class UserDeleteResponse(
    val message: String?,
    val success: Boolean,
    val user_id: String?
)

