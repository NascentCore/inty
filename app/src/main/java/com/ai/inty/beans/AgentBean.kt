package com.ai.inty.beans
import android.os.Parcelable
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import kotlinx.android.parcel.Parcelize


@Parcelize
@JsonClass(generateAdapter = true)
data class AgentInfo(
    @Json(name = "avatar")
    val avatar: String = "",
    @Json(name = "category")
    val category: String = "",
    @Json(name = "gender")
    val gender: String = "",
    @Json(name = "id")
    val id: String = "",
    @Json(name = "is_followed")
    val isFollowed: Boolean = false,
    @Json(name = "name")
    val name: String = "",
    @Json(name = "opening")
    val opening: String = "",
    @Json(name = "voice_preview")
    val voicePreview: String = "",
    @Json(name = "created_at")
    val createdAt: String = "",
    @Json(name = "creator")
    val creator: CreatorInfo? = null
): Parcelable

@Parcelize
@JsonClass(generateAdapter = true)
data class CreatorInfo(
    @Json(name = "age_group")
    val ageGroup: String? = null,
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
): Parcelable


@JsonClass(generateAdapter = true)
data class AgentInfoResponse(
    val list: List<AgentInfo>? = null
)