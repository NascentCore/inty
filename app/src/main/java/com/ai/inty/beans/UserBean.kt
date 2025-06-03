package com.ai.inty.beans

import com.squareup.moshi.JsonClass

data class UserBean(
    var uid: String = "",
    var token: String = ""
)

@JsonClass(generateAdapter = true)
data class CreateGuestReq(
    val device_id: String,
    val system_language: String
)

@JsonClass(generateAdapter = true)
data class CreateGuestResult(
    val guest_id: String,
    val token: String,
    val is_new_guest: Boolean,
)