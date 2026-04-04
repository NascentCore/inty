package com.ai.imate.data

import com.squareup.moshi.Json

data class ApiEnvelope<T>(
    val code: Int,
    val message: String? = null,
    val data: T? = null,
)

data class LoginRequest(
    @param:Json(name = "id_token") val idToken: String? = null,
    val email: String? = null,
    val password: String? = null,
)

data class LoginPayload(
    val token: String,
    val user: LoginUserPayload,
)

data class LoginUserPayload(
    val id: String,
    val email: String? = null,
    val nickname: String? = null,
)

data class UserSession(
    val token: String,
    val userId: String,
    val email: String,
    val nickname: String,
)
