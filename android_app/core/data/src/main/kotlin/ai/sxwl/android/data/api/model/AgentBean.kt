package ai.sxwl.android.data.api.model

import ai.sxwl.android.data.api.getCdnImageUrl
import android.os.Parcelable
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import kotlin.time.Duration.Companion.days
import kotlin.time.Duration.Companion.milliseconds
import kotlin.time.Duration.Companion.seconds
import kotlinx.parcelize.Parcelize
import kotlinx.parcelize.RawValue

@Parcelize
@JsonClass(generateAdapter = true)
data class AgentInfo(
    val avatar: String = "", // 头像
    val background: String = "", // 背景图
    @Json(name = "background_animated") val backgroundAnimatedUrl: String = "", // 背景动图
    @Json(name = "background_images") val backgroundImages: List<String> = emptyList(),
    val category: String = "",
    val gender: String = "",
    val id: String = "",
    @Json(name = "readable_id") val readableId: String = "",
    @Json(name = "is_followed") val isFollowed: Boolean = false,
    val name: String = "",
    val opening: String = "",
    val opening_audio_url: String = "", // 开场白音频url
    @Json(name = "voice_preview") val voicePreview: String = "",
    @Json(name = "created_at") val createdAt: String = "",
    val creator: CreatorInfo? = null,
    val intro: String = "",
    val tags: List<String?>? = null, // tags
    val settings: @RawValue Map<String, Any>? = null,
    val visibility: String = "",
    val prompt: String = "",
    @Json(name = "energy_points") val energyPoints: Int = 0,
    @Json(name = "follower_count") val followerCount: Int = 0,
    @Json(name = "connector_count") val connectorCount: Int = 0,
    @Json(name = "deleted_at") val deletedAt: Long? = null,
    val features: Features? = null,
) : Parcelable {
    // 本地使用的属性数据，非接口字段
    var isDeleted: Boolean = false // 标记该agent是否被服务端已经删除

    // 头像的url获取，根据尺寸比例 和quality
    fun getSmallAvatar(): String? {
        return getCdnImageUrl(avatar, width = 128)
    }

    fun getMediumAvatar(): String? {
        return getCdnImageUrl(avatar, width = 256)
    }

    fun getLargeAvatar(): String? {
        return getCdnImageUrl(avatar, width = 512)
    }

    // 背景图的获取
    fun getMediumBackground(): String? {
        return getCdnImageUrl(background, width = 540)
    }

    fun getLargeBackground(): String? {
        return getCdnImageUrl(background, width = 720)
    }

    // 用于显示的图
    fun getAlbumImage(): String? {
        return getLargeBackground()?.ifEmpty { getLargeAvatar() }
    }

    // 获取可用的原图url，优先背景图，avatar做兜底
    fun getOriginShowImage(): String? {
        return background.takeIf { it.isNotBlank() } ?: avatar.takeIf { it.isNotBlank() }
    }

    val isNew: Boolean
        get() =
            createdAt.toLongOrNull()?.let {
                System.currentTimeMillis().milliseconds - it.seconds <= 30.days
            } ?: false

    /**
     * 当 agent 使用 minimax/minimax-m2-her 时，聊天中动作描述用 *...* 标记而非括号。 “double asterisk” 为模型侧命名，实际为单星号对
     * *...*（** 不参与匹配）。 从 settings.llm_config.model 读取。
     */
    fun useDoubleAsteriskActionMarker(): Boolean {
        val llmConfig = settings?.get("llm_config") as? Map<*, *> ?: return false
        val model = llmConfig["model"] as? String ?: return false
        return model == LLM_MODEL_MINIMAX_M2_HER
    }

    companion object {
        /** llm_config.model 值：此模型使用 *...* 作为动作描述标记。 */
        private const val LLM_MODEL_MINIMAX_M2_HER = "minimax/minimax-m2-her"
    }
}

@Parcelize
@JsonClass(generateAdapter = true)
data class Features(
    @Json(name = "festival_memories") val festivalMemories: List<FestivalMemory> = emptyList(),
    @Json(name = "daily_memories") val dailyMemories: List<DailyMemory> = emptyList(),
) : Parcelable

@Parcelize
@JsonClass(generateAdapter = true)
data class FestivalMemory(
    @Json(name = "memory_id") val memoryId: Long? = null,
    @Json(name = "festival_date") val festivalDate: String = "",
    @Json(name = "festival_name") val festivalName: String? = null,
    val memory: String = "",
) : Parcelable

@Parcelize
@JsonClass(generateAdapter = true)
data class DailyMemory(
    @Json(name = "memory_id") val memoryId: Long? = null,
    @Json(name = "local_date") val localDate: String = "",
    val memory: String = "",
) : Parcelable

@Parcelize
@JsonClass(generateAdapter = true)
data class CreatorInfo(
    @Json(name = "age_group") val ageGroup: String? = null,
    @Json(name = "auth_type") val authType: String = "",
    val avatar: String? = null,
    @Json(name = "created_at") val createdAt: String = "",
    val description: String? = null,
    val email: String? = null,
    val gender: String? = null,
    val id: String = "",
    @Json(name = "is_active") val isActive: Boolean = false,
    @Json(name = "is_superuser") val isSuperuser: Boolean = false,
    val nickname: String = "",
    val phone: String? = null,
    @Json(name = "system_language") val systemLanguage: String = "",
    @Json(name = "updated_at") val updatedAt: String? = null,
    @Json(name = "public_agents_count") val publicAgentsCount: Int = 0,
    @Json(name = "total_public_agents_follows") val totalPublicAgentsFollows: Int = 0,
) : Parcelable

@JsonClass(generateAdapter = true)
data class MatchedAgentImageItem(
    @Json(name = "agent_id") val agentId: String = "",
    @Json(name = "image_url") val imageUrl: String = "",
    @Json(name = "similarity_score") val similarityScore: Double = 0.0,
    @Json(name = "image_description") val imageDescription: String? = null,
)

@JsonClass(generateAdapter = true)
data class AgentInfoResponse(
    val list: List<AgentInfo>? = null,
    val total: Int = 0,
    val page: Int = 1,
    @Json(name = "page_size") val pageSize: Int = 10,
    @Json(name = "total_pages") val totalPages: Int = 1,
    @Json(name = "matched_image_items") val matchedImageItems: List<MatchedAgentImageItem>? = null,
)

@JsonClass(generateAdapter = true)
data class CreateAgentRequest(
    val name: String,
    val gender: String,
    val avatar: String? = null,
    val background: String? = null,
    @Json(name = "background_images") val backgroundImages: List<String> = emptyList(),
    @Json(name = "voice_id") val voiceId: String = "",
    val settings: Map<String, Any> = emptyMap(),
    val intro: String,
    val opening: String,
    val visibility: String,
    val photos: List<String> = emptyList(),
    val category: String = "",
    val prompt: String,
)

@JsonClass(generateAdapter = true) data class GenerateBackgroundRequest(val prompt: String)

@JsonClass(generateAdapter = true)
data class GenerateBackgroundResponse(
    @Json(name = "url") val imageUrl: String = "",
    @Json(name = "urls") val imageUrls: List<String> = listOf(),
)

@JsonClass(generateAdapter = true)
data class UploadAvatarResponse(
    @Json(name = "url") val url: String = "",
    @Json(name = "avatar_url") val avatar_url: String = "",
)

/**
 * 主题专区中的角色项。
 *
 * 该 DTO 用于替代旧的 `AgentService.CharacterThemeItem` 内部嵌套模型依赖，后续迁移时统一使用 `core/data/api/model` 下的类型来源。
 */
@JsonClass(generateAdapter = true)
data class CharacterThemeAgentItem(
    @Json(name = "agent_id") val agentId: String = "",
    @Json(name = "order_index") val orderIndex: Int = 0,
    val agent: AgentInfo? = null,
)

enum class CharacterThemeVisibility {
    @Json(name = "PRIMARY") PRIMARY,
    @Json(name = "SECONDARY") SECONDARY,
    @Json(name = "HIDDEN") HIDDEN,
}

/** 主题专区数据项（Phase 1 Retrofit 迁移目标类型）。 */
@JsonClass(generateAdapter = true)
data class CharacterThemeItem(
    val id: String = "",
    val name: String = "",
    val description: String = "",
    @Json(name = "background_image_url") val backgroundImageUrl: String? = null,
    val visibility: CharacterThemeVisibility = CharacterThemeVisibility.HIDDEN,
    val agents: List<CharacterThemeAgentItem> = emptyList(),
)

@JsonClass(generateAdapter = true)
data class AgentEnergyPointsUpdateRequest(@Json(name = "energy_points") val energyPoints: Int)
