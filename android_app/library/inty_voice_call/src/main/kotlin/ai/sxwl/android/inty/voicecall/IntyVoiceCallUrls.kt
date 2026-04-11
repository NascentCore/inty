package ai.sxwl.android.inty.voicecall

import java.net.URLEncoder
import java.nio.charset.StandardCharsets

object IntyVoiceCallUrls {
    fun liveChatWebSocketUrl(wssBaseUrl: String, agentId: String, token: String): String {
        val base = wssBaseUrl.trimEnd('/')
        val qToken = URLEncoder.encode(token, StandardCharsets.UTF_8).replace("+", "%20")
        return "$base/api/v1/live-chat/$agentId?token=$qToken"
    }
}
