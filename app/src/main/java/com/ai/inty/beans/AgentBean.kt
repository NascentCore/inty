package com.ai.inty.beans
import com.squareup.moshi.JsonClass
import com.squareup.moshi.Json


@JsonClass(generateAdapter = true)
data class AgentInfo(
    @Json(name = "avatar")
    val avatar: String = "",
    @Json(name = "category")
    val category: String = "",
    @Json(name = "description")
    val description: String = "",
    @Json(name = "gender")
    val gender: String = "",
    @Json(name = "id")
    val id: String = "",
    @Json(name = "is_followed")
    val isFollowed: String = "",
    @Json(name = "name")
    val name: String = "",
    @Json(name = "opening")
    val opening: String = "",
    @Json(name = "voice_preview")
    val voicePreview: String = ""
)




