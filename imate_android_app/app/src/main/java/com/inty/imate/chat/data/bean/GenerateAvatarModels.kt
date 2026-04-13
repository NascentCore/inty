package com.inty.imate.chat.data.bean

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class GenerateAvatarRequest(
    val prompt: String,
)

@Serializable
data class GenerateAvatarResponse(
    @SerialName("url") val url: String = "",
    @SerialName("urls") val urls: List<String> = emptyList(),
)

