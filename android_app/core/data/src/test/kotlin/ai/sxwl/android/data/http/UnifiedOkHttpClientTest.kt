package ai.sxwl.android.data.http

import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class UnifiedOkHttpClientTest {
    @Test
    fun shouldApplyChatImageReadTimeout_returnsTrue_forChatImagePostEndpoint() {
        val request =
            Request.Builder()
                .url("https://example.com/api/v1/chat/images/agent-123")
                .post("{}".toRequestBody())
                .build()

        assertTrue(UnifiedOkHttpClient.shouldApplyChatImageReadTimeout(request))
        assertEquals(60, UnifiedOkHttpClient.CHAT_IMAGE_READ_TIMEOUT_SECONDS)
    }

    @Test
    fun shouldApplyChatImageReadTimeout_returnsFalse_forChatImageGetEndpoint() {
        val request =
            Request.Builder().url("https://example.com/api/v1/chat/images/agent-123").get().build()

        assertFalse(UnifiedOkHttpClient.shouldApplyChatImageReadTimeout(request))
    }

    @Test
    fun shouldApplyChatImageReadTimeout_returnsFalse_forOtherPostEndpoint() {
        val request =
            Request.Builder()
                .url("https://example.com/api/v1/chat/music/agent-123")
                .post("{}".toRequestBody())
                .build()

        assertFalse(UnifiedOkHttpClient.shouldApplyChatImageReadTimeout(request))
    }
}
