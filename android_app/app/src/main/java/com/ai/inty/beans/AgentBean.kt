package com.ai.inty.beans

import android.os.Parcelable
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import kotlinx.parcelize.Parcelize
import kotlinx.parcelize.RawValue

@Parcelize
@JsonClass(generateAdapter = true)
data class AgentInfo(
    val avatar: String = "",
    val background: String = "",
    @Json(name = "background_images")
    val backgroundImages: List<String> = emptyList(),
    val category: String = "",
    val gender: String = "",
    val id: String = "",
    @Json(name = "readable_id")
    val readableId: String = "",
    @Json(name = "is_followed")
    val isFollowed: Boolean = false,
    val name: String = "",
    val opening: String = "",
    @Json(name = "voice_preview")
    val voicePreview: String = "",
    @Json(name = "created_at")
    val createdAt: String = "",
    val creator: CreatorInfo? = null,
    val intro: String = "",
    val settings: @RawValue Map<String, Any>? = null,
    val visibility: String = "",
    val prompt: String = "",
    @Json(name = "follower_count")
    val followerCount: Int = 0,
    @Json(name = "connector_count")
    val connectorCount: Int = 0,
    @Json(name = "deleted_at")
    val deletedAt: Long? = null,
) : Parcelable {
    //本地使用的属性数据，非接口字段
    var isDeleted: Boolean = false//标记该agent是否被服务端已经删除
}

@Parcelize
@JsonClass(generateAdapter = true)
data class CreatorInfo(
    @Json(name = "age_group")
    val ageGroup: String? = null,
    @Json(name = "auth_type")
    val authType: String = "",
    val avatar: String? = null,
    @Json(name = "created_at")
    val createdAt: String = "",
    val description: String? = null,
    val email: String? = null,
    val gender: String? = null,
    val id: String = "",
    @Json(name = "is_active")
    val isActive: Boolean = false,
    @Json(name = "is_superuser")
    val isSuperuser: Boolean = false,
    val nickname: String = "",
    val phone: String? = null,
    @Json(name = "system_language")
    val systemLanguage: String = "",
    @Json(name = "updated_at")
    val updatedAt: String? = null,
    @Json(name = "public_agents_count")
    val publicAgentsCount: Int = 0,
    @Json(name = "total_public_agents_follows")
    val totalPublicAgentsFollows: Int = 0,
) : Parcelable

@JsonClass(generateAdapter = true)
data class AgentInfoResponse(
    val list: List<AgentInfo>? = null,
    val total: Int = 0,
    val page: Int = 1,
    @Json(name = "page_size")
    val pageSize: Int = 10,
    @Json(name = "total_pages")
    val totalPages: Int = 1,
)

@JsonClass(generateAdapter = true)
data class FollowResponse(
    val message: String = "",
)

@JsonClass(generateAdapter = true)
data class CreateAgentRequest(
    val name: String,
    val gender: String,
    val avatar: String? = null,
    val background: String? = null,
    @Json(name = "background_images")
    val backgroundImages: List<String> = emptyList(),
    @Json(name = "voice_id")
    val voiceId: String = "",
    val settings: Map<String, Any> = emptyMap(),
    val intro: String,
    val opening: String,
    val visibility: String,
    val photos: List<String> = emptyList(),
    val category: String = "",
    val prompt: String,
)

@JsonClass(generateAdapter = true)
data class CreateAgentResponse(
    val name: String = "",
    val gender: String = "",
    val avatar: String? = null,
    val background: String? = null,
    @Json(name = "voice_id")
    val voiceId: String = "",
    val settings: Map<String, Any>? = null,
    val intro: String = "",
    val opening: String = "",
    val visibility: String = "",
    val photos: List<String> = emptyList(),
    val category: String = "",
    val prompt: String = "",
    val id: String = "",
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
    val creator: CreatorInfo? = null,
)

@JsonClass(generateAdapter = true)
data class GenerateBackgroundRequest(
    val prompt: String,
)

@JsonClass(generateAdapter = true)
data class GenerateBackgroundResponse(
    @Json(name = "url")
    val imageUrl: String = "",
    @Json(name = "urls")
    val imageUrls: List<String> = listOf(),
)

@JsonClass(generateAdapter = true)
data class UploadAvatarResponse(
    @Json(name = "url")
    val url: String = "",
    @Json(name = "avatar_url")
    val avatar_url: String = "",
)
