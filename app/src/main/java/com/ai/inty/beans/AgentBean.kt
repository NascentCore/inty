package com.ai.inty.beans
import android.os.Parcelable
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import kotlinx.parcelize.Parcelize
import kotlinx.parcelize.RawValue


@Parcelize
@JsonClass(generateAdapter = true)
data class AgentInfo(
    @Json(name = "avatar")
    val avatar: String = "",
    @Json(name = "background")
    val background: String = "",
    @Json(name = "background_images")
    val backgroundImages: List<String> = emptyList(),
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
    val creator: CreatorInfo? = null,
    @Json(name = "intro")
    val intro: String = "",
    @Json(name = "settings")
    val settings: @RawValue Map<String, Any>? = null,
    @Json(name = "visibility")
    val visibility: String = "",
    @Json(name = "prompt")
    val prompt: String = "",
    @Json(name = "follower_count")
    val followerCount: Int = 0
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
    val updatedAt: String? = null,
    @Json(name = "public_agents_count")
    val publicAgentsCount: Int = 0,
    @Json(name = "total_public_agents_follows")
    val totalPublicAgentsFollows: Int = 0
): Parcelable


@JsonClass(generateAdapter = true)
data class AgentInfoResponse(
    val list: List<AgentInfo>? = null,
    val total: Int = 0,
    val page: Int = 1,
    @Json(name = "page_size")
    val pageSize: Int = 10,
    @Json(name = "total_pages")
    val totalPages: Int = 1
)

@JsonClass(generateAdapter = true)
data class FollowResponse(
    val message: String = ""
)

@JsonClass(generateAdapter = true)
data class CreateAgentRequest(
    @Json(name = "name")
    val name: String,
    @Json(name = "gender")
    val gender: String,
    @Json(name = "avatar")
    val avatar: String? = null,
    @Json(name = "background")
    val background: String? = null,
    @Json(name = "background_images")
    val backgroundImages: List<String> = emptyList(),
    @Json(name = "voice_id")
    val voiceId: String = "",
    @Json(name = "settings")
    val settings: Map<String, Any> = emptyMap(),
    @Json(name = "intro")
    val intro: String,
    @Json(name = "opening")
    val opening: String,
    @Json(name = "visibility")
    val visibility: String,
    @Json(name = "photos")
    val photos: List<String> = emptyList(),
    @Json(name = "category")
    val category: String = "",
    @Json(name = "prompt")
    val prompt: String
)

@JsonClass(generateAdapter = true)
data class CreateAgentResponse(
    @Json(name = "name")
    val name: String = "",
    @Json(name = "gender")
    val gender: String = "",
    @Json(name = "avatar")
    val avatar: String? = null,
    @Json(name = "background")
    val background: String? = null,
    @Json(name = "voice_id")
    val voiceId: String = "",
    @Json(name = "settings")
    val settings: Map<String, Any>? = null,
    @Json(name = "intro")
    val intro: String = "",
    @Json(name = "opening")
    val opening: String = "",
    @Json(name = "visibility")
    val visibility: String = "",
    @Json(name = "photos")
    val photos: List<String> = emptyList(),
    @Json(name = "category")
    val category: String = "",
    @Json(name = "prompt")
    val prompt: String = "",
    @Json(name = "id")
    val id: String = "",
    @Json(name = "status")
    val status: String = "",
    @Json(name = "creator_id")
    val creatorId: String = "",
    @Json(name = "created_at")
    val createdAt: String = "",
    @Json(name = "updated_at")
    val updatedAt: String? = null,
    @Json(name = "is_followed")
    val isFollowed: Boolean = false,
    @Json(name = "follower_count")
    val followerCount: Int = 0,
    @Json(name = "creator")
    val creator: CreatorInfo? = null
)

@JsonClass(generateAdapter = true)
data class GenerateBackgroundRequest(
    @Json(name = "prompt")
    val prompt: String
)

@JsonClass(generateAdapter = true)
data class GenerateBackgroundResponse(
    @Json(name = "url")
    val imageUrl: String = "",
    @Json(name = "urls")
    val imageUrls: List<String> = listOf()
)

@JsonClass(generateAdapter = true)
data class UploadAvatarResponse(
    @Json(name = "url")
    val url: String = "",
    @Json(name = "filename")
    val filename: String = "",
    @Json(name = "size")
    val size: Long = 0,
    @Json(name = "content_type")
    val contentType: String = ""
)