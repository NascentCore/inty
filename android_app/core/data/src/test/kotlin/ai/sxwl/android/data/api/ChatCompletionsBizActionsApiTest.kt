package ai.sxwl.android.data.api

import ai.sxwl.android.data.api.model.SendMsgResponse
import com.squareup.moshi.Json
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.util.UUID
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assume.assumeTrue
import org.junit.Test


// TODO: 确认该测试确实已经运行并且调用了后端
/**
 * Integration test for chat completions API returning business_actions.
 * Only runs when backend is available and RUN_LOCALHOST_CHAT_COMPLETIONS_TEST=true,
 * so CI (no backend) skips it without failure.
 */
class ChatCompletionsBizActionsApiTest {
    private val client = OkHttpClient()
    private val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()

    @Test
    fun chatCompletions_returnsBusinessActionsList() {
        assumeTrue(
            "Skipped: set RUN_LOCALHOST_CHAT_COMPLETIONS_TEST=true to run against local backend",
            System.getenv(RUN_LOCALHOST_CHAT_COMPLETIONS_TEST) == "true",
        )
        val token = createGuestToken()
        val agentId = createAgent(token)

        try {
            val chatResponse = sendChatCompletion(token, agentId)
            assertEquals(200, chatResponse.code)

            val data = chatResponse.data
            assertNotNull(data)

            val businessActions = data?.businessActions ?: emptyList()
            assertFalse("businessActions should not be empty", businessActions.isEmpty())
            businessActions.forEach { action ->
                assertNotNull("action_type must be non-null", action.actionType)
                assertNotNull("message must be non-null", action.message)
            }
        } finally {
            deleteAgent(token, agentId)
        }
    }

    private fun createGuestToken(): String {
        val payload =
            """
            {
              "device_id": "kotlin-biz-actions-${UUID.randomUUID()}",
              "system_language": "en",
              "age_group": "adult"
            }
            """
                .trimIndent()
        val request =
            Request.Builder()
                .url("$baseUrl/api/v1/auth/guest")
                .post(payload.toRequestBody(jsonMediaType))
                .build()
        val responseBody = executeAndReadBody(request)
        val response = decode(responseBody, GuestApiResponse::class.java)
        assertEquals(200, response.code)

        val token = response.data?.token
        assertNotNull(token)
        return token!!
    }

    private fun createAgent(token: String): String {
        val payload =
            """
            {
              "name": "Kotlin BizAction ${UUID.randomUUID()}",
              "gender": "FEMALE",
              "visibility": "PRIVATE",
              "personality": "Friendly test companion",
              "scenario": "Used for API integration test",
              "intro": "Integration test companion",
              "opening": "Hello from Kotlin integration test"
            }
            """
                .trimIndent()
        val request =
            Request.Builder()
                .url("$baseUrl/api/v1/ai/agents")
                .header("Authorization", bearerToken(token))
                .post(payload.toRequestBody(jsonMediaType))
                .build()
        val responseBody = executeAndReadBody(request)
        val response = decode(responseBody, CreateAgentApiResponse::class.java)
        assertEquals(200, response.code)

        val agentId = response.data?.id
        assertNotNull(agentId)
        return agentId!!
    }

    private fun sendChatCompletion(token: String, agentId: String): SendMsgResponse {
        val payload =
            """
            {
              "messages": [
                {
                  "role": "user",
                  "content": "Hello, can you tell me something fun?"
                }
              ],
              "stream": false,
              "model": "chatbot",
              "language": "en"
            }
            """
                .trimIndent()
        val request =
            Request.Builder()
                .url("$baseUrl/api/v1/chat/completions/$agentId")
                .header("Authorization", bearerToken(token))
                .post(payload.toRequestBody(jsonMediaType))
                .build()
        val responseBody = executeAndReadBody(request)
        return decode(responseBody, SendMsgResponse::class.java)
    }

    private fun deleteAgent(token: String, agentId: String) {
        val request =
            Request.Builder()
                .url("$baseUrl/api/v1/ai/agents/$agentId")
                .header("Authorization", bearerToken(token))
                .delete()
                .build()
        client.newCall(request).execute().close()
    }

    private fun executeAndReadBody(request: Request): String {
        client.newCall(request).execute().use { response ->
            val responseBody = response.body?.string()
            assertEquals("Expected HTTP 200", 200, response.code)
            assertNotNull(responseBody)
            return responseBody!!
        }
    }

    private fun <T> decode(json: String, modelClass: Class<T>): T {
        val parsed = moshi.adapter(modelClass).fromJson(json)
        return checkNotNull(parsed) {
            "Failed to decode response for ${modelClass.simpleName}: $json"
        }
    }

    private fun bearerToken(token: String): String = "Bearer $token"

    private data class GuestApiResponse(
        val code: Int? = null,
        val message: String? = null,
        val data: GuestApiData? = null,
    )

    private data class GuestApiData(
        @Json(name = "guest_id") val guestId: String = "",
        val token: String = "",
    )

    private data class CreateAgentApiResponse(
        val code: Int? = null,
        val message: String? = null,
        val data: CreateAgentApiData? = null,
    )

    private data class CreateAgentApiData(val id: String = "")

    private companion object {
        const val RUN_LOCALHOST_CHAT_COMPLETIONS_TEST = "RUN_LOCALHOST_CHAT_COMPLETIONS_TEST"
        const val baseUrl: String = "http://localhost:8000"
        val jsonMediaType = "application/json; charset=utf-8".toMediaType()
    }
}
