package ai.sxwl.android.data.api.model

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class TextToSpeechVoiceOption(
    @Json(name = "voice_id") val voiceId: String = "",
    val name: String = "",
    val provider: String = "",
    val category: String? = null,
)
