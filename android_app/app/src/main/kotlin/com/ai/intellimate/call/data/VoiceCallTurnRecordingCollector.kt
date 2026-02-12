package com.ai.intellimate.call.data

import ai.sxwl.android.utils.LogUtils
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException

/** 单轮语音录音输出（WAV 文件） */
data class VoiceCallTurnRecordingOutput(
    val voiceTurnId: String,
    val filePath: String,
    val durationMs: Long,
)

/** turn 录音统计（用于调试日志） */
data class VoiceCallTurnBufferStat(
    val turnId: String,
    val chunkCount: Int,
    val totalBytes: Long,
)

/** 录音收集器统计快照（用于调试日志） */
data class VoiceCallTurnCollectorStats(
    val turnCount: Int,
    val totalChunkCount: Int,
    val totalBytes: Long,
    val turns: List<VoiceCallTurnBufferStat>,
)

/**
 * 语音通话“按轮次”录音收集器。
 *
 * 说明：
 * - 每个 turn_id 对应一个临时 PCM 文件；
 * - 通话结束时统一导出为 WAV，供聊天页按 turn 精确关联回放。
 */
class VoiceCallTurnRecordingCollector(
    private val filesDir: File,
    private val sampleRate: Int = 24000,
    private val channelCount: Int = 1,
    private val bitsPerSample: Int = 16,
) {
    private data class TurnBuffer(
        val turnId: String,
        val tempPcmFile: File,
        var outputStream: BufferedOutputStream?,
        var totalBytesWritten: Long = 0L,
        var chunkCount: Int = 0,
    )

    private val lock = Any()
    private val tempDir = File(filesDir, "voice_call_turn_records_tmp").apply { mkdirs() }
    private val outputDir = File(filesDir, "voice_call_turn_records").apply { mkdirs() }
    private val turnBuffers = linkedMapOf<String, TurnBuffer>()
    private var isFinalized = false
    private var finalizedOutputs: List<VoiceCallTurnRecordingOutput>? = null

    /** 追加某一轮的 PCM 音频数据。 */
    fun appendPcmData(voiceTurnId: String, audioBytes: ByteArray) {
        if (audioBytes.isEmpty()) return
        val normalizedTurnId = voiceTurnId.trim()
        if (normalizedTurnId.isBlank()) return

        synchronized(lock) {
            if (isFinalized) return
            val buffer = turnBuffers[normalizedTurnId] ?: createTurnBuffer(normalizedTurnId) ?: return
            val stream = buffer.outputStream ?: return
            runCatching {
                    stream.write(audioBytes)
                    buffer.totalBytesWritten += audioBytes.size.toLong()
                    buffer.chunkCount += 1
                }
                .onFailure {
                    LogUtils.e("写入 turn 录音失败: turnId=$normalizedTurnId, error=${it.message}")
                }
            if (buffer.chunkCount == 1 || buffer.chunkCount % 25 == 0) {
                LogUtils.i(
                    "voice_turn_chunk_stats: turnId=${buffer.turnId}, chunks=${buffer.chunkCount}, bytes=${buffer.totalBytesWritten}"
                )
            }
        }
    }

    /**
     * 完成录音并导出所有 turn 对应的 WAV 文件。
     *
     * @param sessionId 会话 ID，仅用于文件命名和调试
     */
    fun finalizeAllAndExport(sessionId: String): List<VoiceCallTurnRecordingOutput> {
        synchronized(lock) {
            if (isFinalized) return finalizedOutputs.orEmpty()
            isFinalized = true
            val safeSessionId = sanitizeId(sessionId.ifBlank { "unknown_session" })
            val preFinalizeStats = snapshotStatsUnsafe()
            LogUtils.i(
                "voice_turn_finalize_begin: sessionId=$sessionId, turns=${preFinalizeStats.turnCount}, chunks=${preFinalizeStats.totalChunkCount}, bytes=${preFinalizeStats.totalBytes}, details=${formatStatsDetails(preFinalizeStats.turns)}"
            )

            val outputs = buildList {
                turnBuffers.values.forEach { buffer ->
                    runCatching {
                            buffer.outputStream?.flush()
                            buffer.outputStream?.close()
                        }
                        .onFailure {
                            LogUtils.e("关闭 turn 临时录音流失败: turnId=${buffer.turnId}, error=${it.message}")
                        }
                    buffer.outputStream = null

                    if (buffer.totalBytesWritten <= 0L || !buffer.tempPcmFile.exists()) {
                        buffer.tempPcmFile.delete()
                        return@forEach
                    }

                    val safeTurnId = sanitizeId(buffer.turnId)
                    val targetWavFile =
                        File(
                            outputDir,
                            "voice_call_${safeSessionId}_${safeTurnId}_${System.currentTimeMillis()}.wav",
                        )

                    val exported =
                        runCatching {
                                FileInputStream(buffer.tempPcmFile).use { pcmInput ->
                                    FileOutputStream(targetWavFile).use { wavOutput ->
                                        writeTurnWavHeader(
                                            output = wavOutput,
                                            pcmDataSize = buffer.totalBytesWritten,
                                            sampleRate = sampleRate,
                                            channels = channelCount,
                                            bitsPerSample = bitsPerSample,
                                        )
                                        pcmInput.copyTo(wavOutput)
                                    }
                                }
                                true
                            }
                            .onFailure {
                                LogUtils.e(
                                    "导出 turn 录音失败: turnId=${buffer.turnId}, error=${it.message}"
                                )
                            }
                            .getOrDefault(false)

                    buffer.tempPcmFile.delete()
                    if (!exported || !targetWavFile.exists()) return@forEach

                    val bytesPerSecond = sampleRate * channelCount * (bitsPerSample / 8)
                    val durationMs =
                        if (bytesPerSecond > 0) {
                            (buffer.totalBytesWritten * 1000L / bytesPerSecond).coerceAtLeast(0L)
                        } else {
                            0L
                        }

                    add(
                        VoiceCallTurnRecordingOutput(
                            voiceTurnId = buffer.turnId,
                            filePath = targetWavFile.absolutePath,
                            durationMs = durationMs,
                        )
                    )
                }
            }
            turnBuffers.clear()
            finalizedOutputs = outputs
            LogUtils.i(
                "voice_turn_finalize_end: sessionId=$sessionId, exportedTurns=${outputs.size}, exportedDurationMs=${outputs.sumOf { it.durationMs }}, exportedIds=${outputs.joinToString(",") { it.voiceTurnId }}"
            )
            return outputs
        }
    }

    /** 获取当前统计快照（线程安全）。 */
    fun snapshotStats(): VoiceCallTurnCollectorStats {
        synchronized(lock) { return snapshotStatsUnsafe() }
    }

    /** 放弃录音并清理临时文件。 */
    fun discard() {
        synchronized(lock) {
            if (isFinalized) return
            isFinalized = true
            turnBuffers.values.forEach { buffer ->
                runCatching { buffer.outputStream?.close() }
                buffer.outputStream = null
                buffer.tempPcmFile.delete()
            }
            turnBuffers.clear()
        }
    }

    private fun createTurnBuffer(turnId: String): TurnBuffer? {
        val tempFile =
            File(
                tempDir,
                "voice_turn_tmp_${sanitizeId(turnId)}_${System.currentTimeMillis()}_${System.nanoTime()}.pcm",
            )
        val stream =
            runCatching { BufferedOutputStream(FileOutputStream(tempFile)) }
                .onFailure {
                    LogUtils.e("初始化 turn 录音临时文件失败: turnId=$turnId, error=${it.message}")
                }
                .getOrNull()
                ?: return null
        return TurnBuffer(turnId = turnId, tempPcmFile = tempFile, outputStream = stream)
            .also {
                turnBuffers[turnId] = it
                LogUtils.i("voice_turn_opened: turnId=$turnId, totalTurns=${turnBuffers.size}")
            }
    }

    private fun sanitizeId(raw: String): String {
        val normalized = raw.trim().ifBlank { "unknown" }
        return normalized.replace(Regex("[^A-Za-z0-9._-]"), "_")
    }

    private fun snapshotStatsUnsafe(): VoiceCallTurnCollectorStats {
        val turnStats =
            turnBuffers.values.map { buffer ->
                VoiceCallTurnBufferStat(
                    turnId = buffer.turnId,
                    chunkCount = buffer.chunkCount,
                    totalBytes = buffer.totalBytesWritten,
                )
            }
        return VoiceCallTurnCollectorStats(
            turnCount = turnStats.size,
            totalChunkCount = turnStats.sumOf { it.chunkCount },
            totalBytes = turnStats.sumOf { it.totalBytes },
            turns = turnStats,
        )
    }

    private fun formatStatsDetails(stats: List<VoiceCallTurnBufferStat>): String {
        return stats.joinToString(";") { stat ->
            "${stat.turnId}[chunks=${stat.chunkCount},bytes=${stat.totalBytes}]"
        }
    }
}

private fun writeTurnWavHeader(
    output: FileOutputStream,
    pcmDataSize: Long,
    sampleRate: Int,
    channels: Int,
    bitsPerSample: Int,
) {
    val byteRate = sampleRate * channels * bitsPerSample / 8
    val blockAlign = channels * bitsPerSample / 8
    val chunkSize = 36L + pcmDataSize
    val header = ByteArray(44)

    header[0] = 'R'.code.toByte()
    header[1] = 'I'.code.toByte()
    header[2] = 'F'.code.toByte()
    header[3] = 'F'.code.toByte()
    writeTurnIntLE(header, 4, chunkSize.toInt())
    header[8] = 'W'.code.toByte()
    header[9] = 'A'.code.toByte()
    header[10] = 'V'.code.toByte()
    header[11] = 'E'.code.toByte()
    header[12] = 'f'.code.toByte()
    header[13] = 'm'.code.toByte()
    header[14] = 't'.code.toByte()
    header[15] = ' '.code.toByte()
    writeTurnIntLE(header, 16, 16)
    writeTurnShortLE(header, 20, 1)
    writeTurnShortLE(header, 22, channels)
    writeTurnIntLE(header, 24, sampleRate)
    writeTurnIntLE(header, 28, byteRate)
    writeTurnShortLE(header, 32, blockAlign)
    writeTurnShortLE(header, 34, bitsPerSample)
    header[36] = 'd'.code.toByte()
    header[37] = 'a'.code.toByte()
    header[38] = 't'.code.toByte()
    header[39] = 'a'.code.toByte()
    writeTurnIntLE(header, 40, pcmDataSize.toInt())

    try {
        output.write(header)
    } catch (e: IOException) {
        throw IOException("写入 turn WAV 头失败: ${e.message}", e)
    }
}

private fun writeTurnIntLE(buffer: ByteArray, offset: Int, value: Int) {
    buffer[offset] = (value and 0xFF).toByte()
    buffer[offset + 1] = ((value shr 8) and 0xFF).toByte()
    buffer[offset + 2] = ((value shr 16) and 0xFF).toByte()
    buffer[offset + 3] = ((value shr 24) and 0xFF).toByte()
}

private fun writeTurnShortLE(buffer: ByteArray, offset: Int, value: Int) {
    buffer[offset] = (value and 0xFF).toByte()
    buffer[offset + 1] = ((value shr 8) and 0xFF).toByte()
}
