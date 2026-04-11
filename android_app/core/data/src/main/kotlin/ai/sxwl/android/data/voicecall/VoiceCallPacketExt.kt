package ai.sxwl.android.data.voicecall

import ai.sxwl.android.data.http.IntyErrorCode
import ai.sxwl.android.inty.voicecall.CallPacket

val CallPacket.errorEnum: IntyErrorCode?
    get() =
        runCatching { errorCode?.let { IntyErrorCode.valueOf(it) } ?: IntyErrorCode.UNKNOWN }
            .getOrNull()
