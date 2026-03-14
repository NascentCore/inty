package ai.sxwl.android.data.api.model

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import kotlinx.serialization.Serializable

@Serializable
@JsonClass(generateAdapter = true)
data class ChatMode(
    val id: String,
    val name: String = "",
    @Json(name = "short_name") val shortName: String = "",
    val description: String = "",
)
