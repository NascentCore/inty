package ai.sxwl.android.data.api.model

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class SurpriseSnapUnlockReq(
    @Json(name = "message_id") val messageId: Long
)

@JsonClass(generateAdapter = true)
data class SurpriseSnapUnlockResp(
    val unlocked: Boolean = true
)