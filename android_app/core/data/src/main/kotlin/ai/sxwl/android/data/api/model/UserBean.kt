package ai.sxwl.android.data.api.model

import android.os.Parcelable
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import kotlinx.parcelize.Parcelize

/**
 * { “read_id”：“字符串”，“昵称”：“字符串”，“头像”：“字符串”，“电子邮件”：“字符串”，“电话”：
 *“字符串”，“性别”：“男性”，“年龄组”：“字符串”，“描述”：“字符串”，“系统语言”：
 *“字符串”，“id”：“字符串”，“auth_type”：“字符串”，“is_active”：true，“created_at”：
 *“2025-07-24T06：06：40。722Z”，“updated_at”：“2025-07-24T06：06：40。722Z”, "is_superuser": 假,
 *“public_agents_count”：0，“total_public_agents_follows”：0，“followers_count”：0，
 *“连接器计数”：0}*/
@JsonClass(generateAdapter = true)
@Parcelize
data class UserProfile(
    @Json(name = "age_group") val ageGroup: String? = null,
    @Json(name = "auth_type") val authType: String = "",
    val avatar: String? = null,
    @Json(name = "created_at") val createdAt: String = "",
//描述是早期的称呼，目前其在App中被称为persona
// Persona 指的是AI角色看到的人类用户的“角色设定”
    val description: String? = null,
    val email: String? = null,
    val gender: String? = null,
    val id: String = "",
    @Json(name = "readable_id") val readableId: String = "",
    @Json(name = "is_active") val isActive: Boolean = false,
    @Json(name = "is_superuser") val isSuperuser: Boolean = false,
    val nickname: String = "",
    val phone: String? = null,
    @Json(name = "system_language") val systemLanguage: String = "",
    @Json(name = "updated_at") val updatedAt: String? = null,
    @Json(name = "public_agents_count") val publicAgentsCount: Int = 0,
    @Json(name = "total_public_agents_follows") val totalAgentsFollows: Int = 0,
    @Json(name = "followers_count") val followerCount: Int = 0,
    @Json(name = "connector_count") val connectorCount: Int = 0,
) : Parcelable {
    /** 性别代指 */
    fun pronouns(): String {
        return when (gender) {
            GENDER.MALE.value -> "He/Him"
            GENDER.FEMALE.value -> "She/Her"
            else -> "They/Them"
        }
    }
}

enum class GENDER(val value: String) {
    MALE("MALE"),
    FEMALE("FEMALE"),
    OTHER("OTHER"),
}

@JsonClass(generateAdapter = true)
data class GoogleLoginRequest(@Json(name = "id_token") val idToken: String)

@JsonClass(generateAdapter = true)
data class GoogleLoginResponse(val token: String, val user: UserProfile)

/** 查看账号删除的接口返回 */
@JsonClass(generateAdapter = true)
data class UserDeletionCheckResponse(
    @Json(name = "active_subscription") val activeSubscription: Boolean,
    @Json(name = "can_delete") val canDelete: Boolean,
    @Json(name = "error_message") val errorMessage: String?,
)

/** 删除账号的结果返回 */
@JsonClass(generateAdapter = true)
data class UserDeleteResponse(
    val message: String?,
    val success: Boolean,
    @Json(name = "user_id") val userId: String?,
)
