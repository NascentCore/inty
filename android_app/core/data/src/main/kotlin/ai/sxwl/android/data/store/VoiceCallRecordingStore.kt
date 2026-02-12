package ai.sxwl.android.data.store

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.architecture.httplib.utils.MoshiUtils
import java.io.File
import java.io.IOException
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.voiceCallRecordingDataStore by
    preferencesDataStore(name = "voice_call_recording_cache")

/** 语音通话录音条目，通过 voiceSessionId 与文本消息精确关联。 */
data class VoiceCallRecordingEntry(
    val agentId: String,
    val voiceSessionId: String,
    val recordingPath: String,
    val recordingDurationMs: Long = 0L,
    val createdAtMs: Long = System.currentTimeMillis(),
)

/** 语音通话录音缓存结构。 */
data class VoiceCallRecordingCache(
    val entries: List<VoiceCallRecordingEntry> = emptyList()
)

/**
 * 语音通话录音缓存存储。
 *
 * 作用：
 * - 将「voice session id -> 本地录音文件」持久化；
 * - 聊天页渲染 voice bubble 时按 session 精确关联回放按钮，避免错配。
 */
object VoiceCallRecordingStore {
    private val CACHE_KEY = stringPreferencesKey("voice_call_recording_cache_json")
    private const val MAX_CACHE_ENTRIES = 200

    suspend fun saveOrUpdate(context: Context, entry: VoiceCallRecordingEntry) {
        val normalized = entry.normalize()
        if (normalized.voiceSessionId.isBlank() || normalized.recordingPath.isBlank()) return
        val file = File(normalized.recordingPath)
        if (!file.exists() || !file.isFile) return

        val current = readCache(context)
        val merged =
            (
                    current.entries
                        .asSequence()
                        .filter { it.voiceSessionId != normalized.voiceSessionId }
                        .filter { it.isValid() }
                        .toList() + normalized
                )
                .sortedByDescending { it.createdAtMs }
                .take(MAX_CACHE_ENTRIES)

        writeCache(context, VoiceCallRecordingCache(entries = merged))
    }

    suspend fun readByAgent(context: Context, agentId: String): List<VoiceCallRecordingEntry> {
        if (agentId.isBlank()) return emptyList()
        return readCache(context)
            .entries
            .asSequence()
            .map { it.normalize() }
            .filter { it.agentId == agentId }
            .filter { it.isValid() }
            .sortedByDescending { it.createdAtMs }
            .toList()
    }

    suspend fun readBySessionId(context: Context, voiceSessionId: String): VoiceCallRecordingEntry? {
        if (voiceSessionId.isBlank()) return null
        return readCache(context)
            .entries
            .asSequence()
            .map { it.normalize() }
            .firstOrNull { it.voiceSessionId == voiceSessionId && it.isValid() }
    }

    private suspend fun readCache(context: Context): VoiceCallRecordingCache {
        val json =
            context.voiceCallRecordingDataStore.data
                .catch { exception ->
                    if (exception is IOException) {
                        emit(emptyPreferences())
                    } else {
                        throw exception
                    }
                }
                .map { preferences -> preferences[CACHE_KEY].orEmpty() }
                .first()

        if (json.isBlank()) return VoiceCallRecordingCache()
        return runCatching { MoshiUtils.fromJson<VoiceCallRecordingCache>(json) }.getOrNull()
            ?: VoiceCallRecordingCache()
    }

    private suspend fun writeCache(context: Context, cache: VoiceCallRecordingCache) {
        val json = MoshiUtils.toJson(cache)
        context.voiceCallRecordingDataStore.edit { preferences ->
            preferences[CACHE_KEY] = json
        }
    }

    private fun VoiceCallRecordingEntry.normalize(): VoiceCallRecordingEntry {
        return copy(
            agentId = agentId.trim(),
            voiceSessionId = voiceSessionId.trim(),
            recordingPath = recordingPath.trim(),
            createdAtMs = createdAtMs.takeIf { it > 0 } ?: System.currentTimeMillis(),
            recordingDurationMs = recordingDurationMs.coerceAtLeast(0L),
        )
    }

    private fun VoiceCallRecordingEntry.isValid(): Boolean {
        if (agentId.isBlank() || voiceSessionId.isBlank() || recordingPath.isBlank()) return false
        val file = File(recordingPath)
        return file.exists() && file.isFile
    }
}
