package com.ai.intellimate.tips

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
 * CREATED_BY_AGENT: cursor-gpt-5.2
 *
 * 从 assets 读取 tips 列表，并提供随机挑选能力。
 *
 * 文件位置：android_app/app/src/main/assets/intellimate_tips.json 设计目标：方便你后续直接往 JSON 里追加 tips，不需要改代码。
 */
object IntelliMateTipsRepository {

    private const val ASSET_FILE_NAME = "intellimate_tips.json"

    private val moshi: Moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
    private val adapter = moshi.adapter(IntelliMateTipsFile::class.java)

    @Volatile private var cachedTips: List<IntelliMateTip> = emptyList()

    suspend fun getRandomTipText(context: Context): String? {
        val tips = loadTipsIfNeeded(context)
        return tips.randomOrNull()?.text?.takeIf { it.isNotBlank() }
    }

    private suspend fun loadTipsIfNeeded(context: Context): List<IntelliMateTip> {
        val current = cachedTips
        if (current.isNotEmpty()) return current

        return withContext(Dispatchers.IO) {
            val loaded =
                try {
                    val json =
                        context.assets.open(ASSET_FILE_NAME).bufferedReader().use { it.readText() }
                    adapter.fromJson(json)?.tips.orEmpty().filter { it.text.isNotBlank() }
                } catch (e: IOException) {
                    LogUtils.w("IntelliMateTipsRepository", "读取 tips 失败: ${e.message}")
                    emptyList()
                } catch (e: JsonDataException) {
                    LogUtils.w("IntelliMateTipsRepository", "解析 tips 失败(JsonData): ${e.message}")
                    emptyList()
                } catch (e: JsonEncodingException) {
                    LogUtils.w("IntelliMateTipsRepository", "解析 tips 失败(Encoding): ${e.message}")
                    emptyList()
                }

            cachedTips = loaded
            loaded
        }
    }
}

private data class IntelliMateTipsFile(
    @Json(name = "CREATED_BY_AGENT") val createdByAgent: String? = null,
    val version: Int? = null,
    val tips: List<IntelliMateTip> = emptyList(),
)

private data class IntelliMateTip(val id: String? = null, val text: String = "")
