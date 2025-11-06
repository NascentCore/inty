package com.example.fcmserverpush

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject

class ResultFetcher(private val client: OkHttpClient) {

    suspend fun fetch(jobId: String): JobResultPayload = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("${ServerConfig.BASE_URL}/results/$jobId")
            .get()
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw IllegalStateException("获取结果失败: ${response.code}")
            }
            val raw = response.body?.string().orEmpty()
            val json = JSONObject(raw)
            val message = json.optJSONObject("result")?.optString("message")
                ?: "处理完成"
            JobResultPayload(jobId = jobId, message = message, rawJson = raw)
        }
    }
}
