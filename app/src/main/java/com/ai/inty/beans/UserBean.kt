package com.ai.inty.beans

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import android.os.Parcelable

data class UserBean(
    var uid: String = "",
    var token: String = ""
)

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
    @Json(name = "avatar")
    val avatar: String? = null,
    @Json(name = "created_at")
    val createdAt: String = "",
    @Json(name = "description")
    val description: String? = null,
    @Json(name = "email")
    val email: String? = null,
    @Json(name = "gender")
    val gender: String? = null,
    @Json(name = "id")
    val id: String = "",
    @Json(name = "readable_id")
    val readableId: String = "",
    @Json(name = "is_active")
    val isActive: Boolean = false,
    @Json(name = "is_superuser")
    val isSuperuser: Boolean = false,
    @Json(name = "nickname")
    val nickname: String = "",
    @Json(name = "phone")
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
    @Json(name = "token")
    val token: String
)

@JsonClass(generateAdapter = true)
data class GoogleLoginRequest(
    @Json(name = "id_token")
    val idToken: String
)

@JsonClass(generateAdapter = true)
data class GoogleLoginResponse(
    @Json(name = "token")
    val token: String,
    @Json(name = "user")
    val user: UserProfile
)