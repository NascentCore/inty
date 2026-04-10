package com.ai.imate.system.report.data

import com.ai.core.data.bean.HttpResult
import com.ai.core.data.exceptions.IntyException
import com.ai.core.http.di.KtorHttpClientSingleton
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import java.io.File
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody

@Serializable
private data class ReportApiEnvelope(
    val code: Int = 200,
    val message: String = "",
    val data: JsonElement? = null,
)

sealed interface CreateReportOutcome {
    data object Success : CreateReportOutcome

    data class BusinessError(val code: Int, val message: String) : CreateReportOutcome

    data object UnprocessableEntity : CreateReportOutcome

    data class TransportError(val message: String) : CreateReportOutcome
}

class ReportRemoteDataSource @Inject constructor() {

    suspend fun createReport(request: ReportCreateRequest): CreateReportOutcome {
        val response = KtorHttpClientSingleton.httpClient.post("/api/v1/report/") { setBody(request) }
        if (response.status.value == 422) {
            return CreateReportOutcome.UnprocessableEntity
        }
        if (response.status.value !in 200..299) {
            val msg =
                runCatching { response.bodyAsText() }.getOrElse { t -> t.message ?: "read failed" }
            return CreateReportOutcome.TransportError(msg)
        }
        val text = response.bodyAsText()
        val json = KtorHttpClientSingleton.ktorHttpJson
        val envelope =
            runCatching { json.decodeFromString(ReportApiEnvelope.serializer(), text) }.getOrElse {
                return CreateReportOutcome.TransportError("parse response")
            }
        if (envelope.code != 200) {
            return CreateReportOutcome.BusinessError(envelope.code, envelope.message)
        }
        return CreateReportOutcome.Success
    }

    suspend fun uploadReportImage(file: File, filename: String): String =
        withContext(Dispatchers.IO) {
            val client = KtorHttpClientSingleton.authenticatedOkHttp()
            val partBody = file.asRequestBody("image/*".toMediaTypeOrNull())
            val body =
                MultipartBody.Builder()
                    .setType(MultipartBody.FORM)
                    .addFormDataPart("file", filename, partBody)
                    .build()
            val url = "${KtorHttpClientSingleton.httpBaseUrlTrimmed()}/api/v1/images"
            val req = Request.Builder().url(url).post(body).build()
            client.newCall(req).execute().use { resp ->
                val text = resp.body?.string().orEmpty()
                if (!resp.isSuccessful) {
                    throw IntyException(resp.code, text.ifBlank { resp.message })
                }
                val json = KtorHttpClientSingleton.ktorHttpJson
                val envelope =
                    runCatching {
                            json.decodeFromString(
                                HttpResult.serializer(UploadAvatarResponse.serializer()),
                                text,
                            )
                        }
                        .getOrElse { throw IntyException(-1, "parse upload response") }
                if (envelope.code != 200) {
                    throw IntyException(envelope.code, envelope.message)
                }
                val data =
                    envelope.data
                        ?: throw IntyException(HttpResult.ErrorCode.EmptyResponse.value, "empty data")
                val resolved = data.url.ifBlank { data.avatarUrl }
                if (resolved.isBlank()) {
                    throw IntyException(-1, "empty url")
                }
                resolved
            }
        }
}
