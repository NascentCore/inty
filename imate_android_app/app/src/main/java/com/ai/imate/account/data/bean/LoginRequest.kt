package com.ai.imate.account.data.bean

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class LoginRequest(
    @SerialName("id_token")
    val idToken: String? = null,
    val email: String? = null,
    val password: String? = null,
)