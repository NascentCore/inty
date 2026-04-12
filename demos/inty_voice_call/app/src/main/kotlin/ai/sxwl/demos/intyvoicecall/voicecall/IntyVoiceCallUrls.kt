package ai.sxwl.demos.intyvoicecall.voicecall

import java.net.URLEncoder
import java.nio.charset.StandardCharsets

object IntyVoiceCallUrls {
    fun liveChatWebSocketUrl(
        wssBaseUrl: String,
        agentId: String,
        speechLanguageCode: String? = null,
        responseLanguageName: String? = null,
    ): String {
        val base = wssBaseUrl.trimEnd('/')
        val sb = StringBuilder("$base/api/v1/live-chat/$agentId")
        val qs = ArrayList<String>()
        speechLanguageCode?.trim()?.takeIf { it.isNotEmpty() }?.let { code ->
            val q = URLEncoder.encode(code, StandardCharsets.UTF_8).replace("+", "%20")
            qs.add("speech_language_code=$q")
        }
        responseLanguageName?.trim()?.takeIf { it.isNotEmpty() }?.let { name ->
            val q = URLEncoder.encode(name, StandardCharsets.UTF_8).replace("+", "%20")
            qs.add("response_language_name=$q")
        }
        if (qs.isNotEmpty()) {
            sb.append('?').append(qs.joinToString("&"))
        }
        return sb.toString()
    }
}
