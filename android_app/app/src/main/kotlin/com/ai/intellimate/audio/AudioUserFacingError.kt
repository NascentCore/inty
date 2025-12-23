package com.ai.intellimate.audio

import androidx.media3.common.PlaybackException

/**
 * CREATED_BY_AGENT
 *
 * 将播放器/网络等底层错误转换为普通人可理解的提示。
 */
internal object AudioUserFacingError {
    fun forPlaybackException(error: PlaybackException): String {
        val reason =
            when (error.errorCode) {
                PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_FAILED,
                PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_TIMEOUT,
                -> "网络连接不稳定，音频没能加载成功"

                PlaybackException.ERROR_CODE_IO_BAD_HTTP_STATUS -> "音频链接暂时不可用（服务器返回异常）"
                PlaybackException.ERROR_CODE_IO_FILE_NOT_FOUND -> "找不到这段音频（可能已过期或被删除）"
                PlaybackException.ERROR_CODE_IO_NO_PERMISSION -> "系统不允许访问这段音频"

                PlaybackException.ERROR_CODE_DECODING_FAILED -> "手机暂时无法解码这段音频"
                PlaybackException.ERROR_CODE_AUDIO_TRACK_INIT_FAILED,
                PlaybackException.ERROR_CODE_AUDIO_TRACK_WRITE_FAILED,
                -> "系统音频输出不可用（可能正在通话或被其它应用占用）"

                PlaybackException.ERROR_CODE_UNSPECIFIED,
                -> null

                else -> null
            }

        val detail = humanizeDetail(error.message)
        return buildMessage(
            reason = reason ?: detail ?: "发生了未知问题",
            suggestion =
                when (error.errorCode) {
                    PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_FAILED,
                    PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_TIMEOUT,
                    PlaybackException.ERROR_CODE_IO_BAD_HTTP_STATUS,
                    -> "你可以检查网络后再试一次"

                    PlaybackException.ERROR_CODE_AUDIO_TRACK_INIT_FAILED,
                    PlaybackException.ERROR_CODE_AUDIO_TRACK_WRITE_FAILED,
                    -> "你可以先关掉其它正在播放声音的应用，再试一次"

                    PlaybackException.ERROR_CODE_IO_FILE_NOT_FOUND -> "你可以刷新页面或稍后再试"
                    PlaybackException.ERROR_CODE_DECODING_FAILED -> "你可以更新应用或稍后再试"
                    else -> "你可以稍后再试一次"
                },
        )
    }

    fun forGenericPlaybackError(raw: String?): String {
        val detail = humanizeDetail(raw)
        return buildMessage(
            reason = detail ?: "发生了未知问题",
            suggestion = "你可以稍后再试一次",
        )
    }

    fun forTtsError(raw: String?): String {
        val reason =
            when {
                raw.isNullOrBlank() -> null
                raw.contains("timeout", ignoreCase = true) ||
                    raw.contains("timed out", ignoreCase = true) ->
                    "生成语音超时了（网络可能不稳定）"

                raw.contains("network", ignoreCase = true) ||
                    raw.contains("UnknownHost", ignoreCase = true) ||
                    raw.contains("Unable to resolve host", ignoreCase = true) ->
                    "网络连接不稳定，没能生成语音"

                raw.contains("429") || raw.contains("rate", ignoreCase = true) -> "请求太频繁了，系统有点忙"
                raw.contains("401") || raw.contains("403") -> "权限校验失败，暂时无法生成语音"
                raw.contains("500") || raw.contains("502") || raw.contains("503") -> "服务器暂时出了点问题"
                else -> null
            }

        return buildMessage(
            reason = reason ?: (humanizeDetail(raw) ?: "发生了未知问题"),
            suggestion = "你可以稍后再试一次",
        )
    }

    private fun buildMessage(reason: String, suggestion: String): String {
        return "音频没能播放出来。原因：$reason。$suggestion。"
    }

    private fun humanizeDetail(raw: String?): String? {
        if (raw.isNullOrBlank()) {
            return null
        }

        val text = raw.trim()
        return when {
            text.contains("Unable to resolve host", ignoreCase = true) ||
                text.contains("UnknownHost", ignoreCase = true) ->
                "网络连接失败（找不到服务器）"

            text.contains("timeout", ignoreCase = true) ||
                text.contains("timed out", ignoreCase = true) ->
                "网络连接超时"

            text.contains("SSL", ignoreCase = true) -> "网络安全连接失败"
            text.contains("Cleartext HTTP traffic", ignoreCase = true) -> "网络连接方式不被允许"
            text.contains("403") -> "没有访问权限"
            text.contains("404") -> "音频链接不存在"
            text.contains("500") || text.contains("502") || text.contains("503") -> "服务器暂时不可用"
            else -> null
        }
    }
}

