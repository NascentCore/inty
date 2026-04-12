package ai.sxwl.demos.intyvoicecall

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.http.HttpHeaders
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ApiResponse<T>(
    val code: Int,
    val message: String,
    val data: T? = null,
)

@Serializable
data class LiveChatStatusData(
    val enabled: Boolean,
    val model: String = "",
    @SerialName("default_voice") val defaultVoice: String = "",
    @SerialName("send_sample_rate") val sendSampleRate: Int = 16000,
    @SerialName("receive_sample_rate") val receiveSampleRate: Int = 24000,
    @SerialName("default_speech_language_code") val defaultSpeechLanguageCode: String? = null,
    @SerialName("default_response_language_name") val defaultResponseLanguageName: String? = null,
)

suspend fun fetchLiveChatStatus(
    httpClient: HttpClient,
    httpsBaseUrl: String,
    bearerToken: String,
): LiveChatStatusData {
    val base = httpsBaseUrl.trimEnd('/')
    val response: ApiResponse<LiveChatStatusData> =
        httpClient.get("$base/api/v1/live-chat/status") {
            header(HttpHeaders.Authorization, "Bearer $bearerToken")
        }
            .body()
    if (response.code != 200 || response.data == null) {
        throw IllegalStateException("live-chat/status failed: code=${response.code} message=${response.message}")
    }
    return response.data
}
