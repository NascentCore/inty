package com.ai.imate.account.data.bean

import kotlinx.serialization.Serializable

@Serializable
data class LoginResponse(val token: String, val user: UserProfile)