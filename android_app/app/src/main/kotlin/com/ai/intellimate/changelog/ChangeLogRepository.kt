package com.ai.intellimate.changelog

import ai.sxwl.android.utils.LogUtils
import android.content.Context
import com.squareup.moshi.Json
import com.squareup.moshi.JsonDataException
import com.squareup.moshi.JsonEncodingException
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.io.IOException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * CREATED_BY_AGENT: gpt-5.2-codex-high
 *
 * 从 assets 读取更新日志列表，供“我的”页面展示。
 *
 * 文件位置：android_app/app/src/main/assets/intellimate_change_logs.json
 */
object ChangeLogRepository {
    private const val ASSET_FILE_NAME = "intellimate_change_logs.json"

    private val moshi: Moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
    private val adapter = moshi.adapter(ChangeLogFile::class.java)

    @Volatile private var cachedLogs: List<ChangeLogEntry> = emptyList()
    @Volatile private var hasLoaded: Boolean = false

    suspend fun getChangeLogs(context: Context): List<ChangeLogEntry> {
        if (hasLoaded) return cachedLogs
        return loadChangeLogs(context)
    }

    private suspend fun loadChangeLogs(context: Context): List<ChangeLogEntry> {
        return withContext(Dispatchers.IO) {
            val loaded = readChangeLogs(context)
            cachedLogs = loaded
            hasLoaded = true
            loaded
        }
    }

    private fun readChangeLogs(context: Context): List<ChangeLogEntry> {
        return try {
            val json = context.assets.open(ASSET_FILE_NAME).bufferedReader().use { it.readText() }
            adapter.fromJson(json)?.logs.orEmpty().mapNotNull { it.sanitizedOrNull() }
        } catch (e: IOException) {
            LogUtils.w("ChangeLogRepository", "读取更新日志失败: ${e.message}")
            emptyList()
        } catch (e: JsonDataException) {
            LogUtils.w("ChangeLogRepository", "解析更新日志失败(JsonData): ${e.message}")
            emptyList()
        } catch (e: JsonEncodingException) {
            LogUtils.w("ChangeLogRepository", "解析更新日志失败(Encoding): ${e.message}")
            emptyList()
        }
    }
}

private data class ChangeLogFile(
    @Json(name = "CREATED_BY_AGENT") val createdByAgent: String? = null,
    @Json(name = "schema_version") val schemaVersion: Int? = null,
    val logs: List<ChangeLogEntry> = emptyList(),
)

data class ChangeLogEntry(
    val id: String? = null,
    @Json(name = "version_name") val versionName: String = "",
    @Json(name = "release_date") val releaseDate: String? = null,
    val highlights: List<String> = emptyList(),
)

private fun ChangeLogEntry.sanitizedOrNull(): ChangeLogEntry? {
    val cleanedVersion = versionName.trim()
    if (cleanedVersion.isEmpty()) return null
    val cleanedHighlights = highlights.mapNotNull { it.trim().takeIf(String::isNotEmpty) }
    return copy(versionName = cleanedVersion, highlights = cleanedHighlights)
}
