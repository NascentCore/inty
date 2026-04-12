package ai.sxwl.android.inty.voicecall

import java.net.URLEncoder
import java.nio.charset.StandardCharsets

object IntyVoiceCallUrls {
    fun liveChatWebSocketUrl(
        wssBaseUrl: String,
        agentId: String,
        token: String,
        speechLanguageCode: String? = null,
        responseLanguageName: String? = null,
    ): String {
        val base = wssBaseUrl.trimEnd('/')
        val qToken = URLEncoder.encode(token, StandardCharsets.UTF_8).replace("+", "%20")
        val sb = StringBuilder("$base/api/v1/live-chat/$agentId?token=$qToken")
        speechLanguageCode?.trim()?.takeIf { it.isNotEmpty() }?.let { code ->
            val q =
                URLEncoder.encode(code, StandardCharsets.UTF_8).replace("+", "%20")
            sb.append("&speech_language_code=").append(q)
        }
        responseLanguageName?.trim()?.takeIf { it.isNotEmpty() }?.let { name ->
            val q =
                URLEncoder.encode(name, StandardCharsets.UTF_8).replace("+", "%20")
            sb.append("&response_language_name=").append(q)
        }
        return sb.toString()
    }
}
