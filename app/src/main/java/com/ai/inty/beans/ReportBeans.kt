package com.ai.inty.beans

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass


@JsonClass(generateAdapter = true)
data class ReportItem(
    val code: String = "",
    val description: String = "",
    val id: Int = 0
)


@JsonClass(generateAdapter = true)
data class ReportReq(
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
    val code: Int = 0,
    val message: String = "",
    val data: String? = null
)