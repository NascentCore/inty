package com.ai.inty.beans

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass


@JsonClass(generateAdapter = true)
data class ReportItem(
    @Json(name = "code")
    val code: String = "",
    @Json(name = "description")
    val description: String = "",
    @Json(name = "id")
    val id: Int = 0,
    @Json(name = "is_active")
    val isActive: Boolean = false
)


@JsonClass(generateAdapter = true)
data class ReportReq(
    @Json(name = "description")
    val description: String = "",
    @Json(name = "image_urls")
    val imageUrls: List<String?> = listOf(),
    @Json(name = "reason_ids")
    val reasonIds: List<Int> = listOf(),
    @Json(name = "target_id")
    val targetId: String,
    @Json(name = "target_type")
    val targetType: String = "USER"
)

@JsonClass(generateAdapter = true)
data class ReportResponse(
    @Json(name = "code")
    val code: Int = 0,
    @Json(name = "message")
    val message: String = "",
    @Json(name = "data")
    val data: String? = null
)