package com.inty.imate.account.data.bean

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class AccountDeletionResponse(
    val success: Boolean,
    val message: String? = null,
    @SerialName("user_id") val userId: String? = null,
)
