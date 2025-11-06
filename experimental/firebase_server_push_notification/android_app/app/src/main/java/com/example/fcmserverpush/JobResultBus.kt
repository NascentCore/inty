package com.example.fcmserverpush

import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow

data class JobResultPayload(
    val jobId: String,
    val message: String,
    val rawJson: String,
)

object JobResultBus {
    private val _results = MutableSharedFlow<JobResultPayload>(
        replay = 0,
        extraBufferCapacity = 1,
        onBufferOverflow = BufferOverflow.DROP_OLDEST,
    )

    val results: SharedFlow<JobResultPayload> = _results

    fun emit(result: JobResultPayload) {
        _results.tryEmit(result)
    }
}
