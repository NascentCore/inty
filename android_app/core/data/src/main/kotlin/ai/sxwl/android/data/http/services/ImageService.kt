package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.data.store.IntySetting
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import java.io.File
import java.util.concurrent.TimeUnit
import org.json.JSONObject

/**
 * 简单直连版图片上传服务：直接用 OkHttp 调用 /api/v1/images。
 * - 认证：使用当前 Inty token（Bearer）
 * - 基址：使用当前 NetworkConfig 的 baseUrl
 * - 错误：直接抛异常，由调用方 try/catch
 */
object ImageService {

    private val httpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    /**
     * 上传用户头像，返回上传后的图片 URL（CDN URL）。
     * 说明：后台返回为 APIResponse，优先取 data.avatar_url，其次 data.url。
     */
    suspend fun uploadUserAvatar(file: File): String = withContext(Dispatchers.IO) {
        if (!file.exists() || file.length() == 0L) {
            throw IllegalArgumentException("无效的图片文件")
        }

        val token = IntySetting.getCurToken()
        if (token.isBlank()) {
            throw IllegalStateException("未登录或 token 为空")
        }

        val baseUrl = NetworkConfig.getBaseUrl().trimEnd('/')
        val url = "$baseUrl/api/v1/images"

        val mediaType = guessImageMediaType(file.name)
        val requestBody: RequestBody = RequestBody.create(mediaType, file)
        val multipartBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", file.name, requestBody)
            .build()

        val request = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Bearer $token")
            .post(multipartBody)
            .build()

        httpClient.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw RuntimeException("上传失败: HTTP ${response.code} ${response.message}")
            }

            val bodyStr = response.body?.string() ?: throw RuntimeException("服务端返回空响应")
            try {
                val json = JSONObject(bodyStr)
                // 兼容形态：有 code/data 的 APIResponse，或扁平返回（容错）
                val dataObj = if (json.has("data")) json.optJSONObject("data") else json
                if (json.has("code") && json.optInt("code", 200) != 200) {
                    val msg = json.optString("message", "上传失败")
                    throw RuntimeException(msg)
                }

                val avatarUrl = dataObj?.optString("avatar_url").orEmpty()
                val urlField = if (avatarUrl.isNotBlank()) avatarUrl else dataObj?.optString("url").orEmpty()

                if (urlField.isBlank()) {
                    throw RuntimeException("解析返回失败：未找到图片 URL")
                }

                return@use urlField
            } catch (e: Exception) {
                // 返回内容非预期 JSON
                throw RuntimeException("响应解析失败: ${e.message}")
            }
        }
    }

    private fun guessImageMediaType(filename: String) = when {
        filename.endsWith(".png", ignoreCase = true) -> "image/png".toMediaTypeOrNull()
        filename.endsWith(".jpg", ignoreCase = true) -> "image/jpeg".toMediaTypeOrNull()
        filename.endsWith(".jpeg", ignoreCase = true) -> "image/jpeg".toMediaTypeOrNull()
        filename.endsWith(".webp", ignoreCase = true) -> "image/webp".toMediaTypeOrNull()
        else -> "image/*".toMediaTypeOrNull()
    }
}
