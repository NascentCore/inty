// 与后端对应的数据类型
// 目前还不使用
// 目标是做到与后端一一对应、方便管理
//
// TODO: 本文件类型与 app/schemas/response.py 对齐，当前为占位、未在项目其他处使用，
// 后续将逐步替换现有响应类型。

package ai.sxwl.android.data.api.model

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

// ----- 与 app/schemas/response.py 对应的占位类型 -----

@JsonClass(generateAdapter = true)
data class PaginationData<T>(
    val list: List<T> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    @Json(name = "page_size") val pageSize: Int = 10,
    @Json(name = "total_pages") val totalPages: Int = 0,
)

@JsonClass(generateAdapter = true)
data class PagedResponse<T>(
    val items: List<T> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    @Json(name = "page_size") val pageSize: Int = 10,
    @Json(name = "total_pages") val totalPages: Int = 0,
)

@JsonClass(generateAdapter = true)
data class APIResponse<T>(
    val code: Int = 200,
    val message: String = "success",
    val data: T? = null,
)

typealias PaginationResponse = APIResponse<PaginationData<*>>

@JsonClass(generateAdapter = true)
data class BizError(
    val code: Int,
    @Json(name = "error_code") val errorCode: String,
    val message: String,
)

@JsonClass(generateAdapter = true)
data class UsageLimitExceeded(
    val code: Int,
    @Json(name = "error_code") val errorCode: String,
    val message: String,
    @Json(name = "used_count") val usedCount: Int,
    @Json(name = "daily_limit") val dailyLimit: Int,
)

/**
 * 业务错误码枚举，与 app/schemas/response.py BusinessErrorCodeEnum 取值一致。 code / message 映射见
 * BusinessErrorCodes.kt，此处仅作占位。
 */
enum class BusinessErrorCodeEnum(val value: String) {
    SUBSCRIPTION_REQUIRED("SUBSCRIPTION_REQUIRED"),
    IMAGE_GENERATION_LIMIT_REACHED("IMAGE_GENERATION_LIMIT_REACHED"),
    AGENT_CREATION_LIMIT_REACHED("AGENT_CREATION_LIMIT_REACHED"),
    VOICE_GENERATION_LIMIT_REACHED("VOICE_GENERATION_LIMIT_REACHED"),
    GUEST_LOGIN_REQUIRED("GUEST_LOGIN_REQUIRED"),
    IMAGE_GENERATION_BLOCKED("IMAGE_GENERATION_BLOCKED"),
    LIVE_CHAT_AGENT_LIMIT_REACHED("LIVE_CHAT_AGENT_LIMIT_REACHED"),
    LIVE_CHAT_DURATION_LIMIT_REACHED("LIVE_CHAT_DURATION_LIMIT_REACHED"),
}
