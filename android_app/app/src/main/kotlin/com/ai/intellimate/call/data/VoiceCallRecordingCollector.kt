package com.ai.intellimate.call.data

import ai.sxwl.android.utils.LogUtils
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException

/** 录音输出结果（WAV 文件） */
data class VoiceCallRecordingOutput(
    val filePath: String,
    val durationMs: Long,
)

/**
 * 语音通话录音收集器。
 *
 * 说明：
 * - 实时接收 PCM（16bit/mono）并先写入临时 PCM 文件；
 * - 通话结束后封装为 WAV，避免在内存中长期累计大数组。
 */
class VoiceCallRecordingCollector(
    private val filesDir: File,
    private val sampleRate: Int = 24000,
    private val channelCount: Int = 1,
    private val bitsPerSample: Int = 16,
) {
    private val lock = Any()
    private val tempDir = File(filesDir, "voice_call_records_tmp").apply { mkdirs() }
    private val outputDir = File(filesDir, "voice_call_records").apply { mkdirs() }
    private val tempPcmFile =
        File(
            tempDir,
            "voice_call_tmp_${System.currentTimeMillis()}_${System.nanoTime()}.pcm",
        )

    private var outputStream: BufferedOutputStream? =
        runCatching { BufferedOutputStream(FileOutputStream(tempPcmFile)) }
            .onFailure { LogUtils.e("初始化录音临时文件失败: ${it.message}") }
            .getOrNull()

    private var totalBytesWritten = 0L
    private var finalizedOutput: VoiceCallRecordingOutput? = null
    private var isFinalized = false

    /** 追加一段 PCM 音频数据 */
    fun appendPcmData(audioBytes: ByteArray) {
        if (audioBytes.isEmpty()) return
        synchronized(lock) {
            if (isFinalized) return
            val stream = outputStream ?: return
            runCatching {
                    stream.write(audioBytes)
                    totalBytesWritten += audioBytes.size.toLong()
                }
                .onFailure { LogUtils.e("写入录音数据失败: ${it.message}") }
        }
    }

    /**
     * 完成录音并导出 WAV 文件。
     *
     * @param sessionId 会话 ID，用于命名和后续精确关联文本记录
     * @return 可播放录音信息；若无有效音频则返回 null
     */
    fun finalizeAndExport(sessionId: String): VoiceCallRecordingOutput? {
        synchronized(lock) {
            if (isFinalized) return finalizedOutput
            isFinalized = true
            runCatching {
                    outputStream?.flush()
                    outputStream?.close()
                }
                .onFailure { LogUtils.e("关闭录音临时流失败: ${it.message}") }
            outputStream = null

            if (totalBytesWritten <= 0L || !tempPcmFile.exists()) {
                tempPcmFile.delete()
                return null
            }

            val safeSessionId = sanitizeSessionId(sessionId)
            val targetWavFile =
                File(outputDir, "voice_call_${safeSessionId}_${System.currentTimeMillis()}.wav")

            val saved =
                runCatching {
                        FileInputStream(tempPcmFile).use { pcmInput ->
                            FileOutputStream(targetWavFile).use { wavOutput ->
                                writeWavHeader(
                                    output = wavOutput,
                                    pcmDataSize = totalBytesWritten,
                                    sampleRate = sampleRate,
                                    channels = channelCount,
                                    bitsPerSample = bitsPerSample,
                                )
                                pcmInput.copyTo(wavOutput)
                            }
                        }
                        true
                    }
                    .onFailure { LogUtils.e("导出录音 WAV 失败: ${it.message}") }
                    .getOrDefault(false)

            tempPcmFile.delete()

            if (!saved || !targetWavFile.exists()) {
                return null
            }

            val bytesPerSecond = sampleRate * channelCount * (bitsPerSample / 8)
            val durationMs =
                if (bytesPerSecond > 0) {
                    (totalBytesWritten * 1000L / bytesPerSecond).coerceAtLeast(0L)
                } else {
                    0L
                }

            return VoiceCallRecordingOutput(
                    filePath = targetWavFile.absolutePath,
                    durationMs = durationMs,
                )
                .also { finalizedOutput = it }
        }
    }

    /** 放弃录音并清理临时文件 */
    fun discard() {
        synchronized(lock) {
            if (isFinalized) return
            isFinalized = true
            runCatching { outputStream?.close() }
            outputStream = null
            tempPcmFile.delete()
        }
    }

    private fun sanitizeSessionId(sessionId: String): String {
        val normalized = sessionId.trim().ifBlank { "unknown_session" }
        return normalized.replace(Regex("[^A-Za-z0-9._-]"), "_")
    }
}

private fun writeWavHeader(
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

    // ChunkID "RIFF"
    header[0] = 'R'.code.toByte()
    header[1] = 'I'.code.toByte()
    header[2] = 'F'.code.toByte()
    header[3] = 'F'.code.toByte()
    // ChunkSize
    writeIntLE(header, 4, chunkSize.toInt())
    // Format "WAVE"
    header[8] = 'W'.code.toByte()
    header[9] = 'A'.code.toByte()
    header[10] = 'V'.code.toByte()
    header[11] = 'E'.code.toByte()
    // Subchunk1ID "fmt "
    header[12] = 'f'.code.toByte()
    header[13] = 'm'.code.toByte()
    header[14] = 't'.code.toByte()
    header[15] = ' '.code.toByte()
    // Subchunk1Size = 16 (PCM)
    writeIntLE(header, 16, 16)
    // AudioFormat = 1 (PCM)
    writeShortLE(header, 20, 1)
    // NumChannels
    writeShortLE(header, 22, channels)
    // SampleRate
    writeIntLE(header, 24, sampleRate)
    // ByteRate
    writeIntLE(header, 28, byteRate)
    // BlockAlign
    writeShortLE(header, 32, blockAlign)
    // BitsPerSample
    writeShortLE(header, 34, bitsPerSample)
    // Subchunk2ID "data"
    header[36] = 'd'.code.toByte()
    header[37] = 'a'.code.toByte()
    header[38] = 't'.code.toByte()
    header[39] = 'a'.code.toByte()
    // Subchunk2Size
    writeIntLE(header, 40, pcmDataSize.toInt())

    try {
        output.write(header)
    } catch (e: IOException) {
        throw IOException("写入 WAV 头失败: ${e.message}", e)
    }
}

private fun writeIntLE(buffer: ByteArray, offset: Int, value: Int) {
    buffer[offset] = (value and 0xFF).toByte()
    buffer[offset + 1] = ((value shr 8) and 0xFF).toByte()
    buffer[offset + 2] = ((value shr 16) and 0xFF).toByte()
    buffer[offset + 3] = ((value shr 24) and 0xFF).toByte()
}

private fun writeShortLE(buffer: ByteArray, offset: Int, value: Int) {
    buffer[offset] = (value and 0xFF).toByte()
    buffer[offset + 1] = ((value shr 8) and 0xFF).toByte()
}
