package com.inty.utils.log.interceptor

import android.os.SystemClock
import com.inty.utils.log.Chain
import com.inty.utils.log.Interceptor
import com.inty.utils.log.Pipeline
import com.inty.utils.log.model.Log
import com.inty.utils.log.model.LogBatch
import com.inty.utils.log.singleLogDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * An [Interceptor] batch [Log] into [LogBatch]
 */
class BatchInterceptor<LOG, LOGS>(
    private val size: Int,
    private val interval: Long,
    private val pipeline: Pipeline<LOG, LOGS>
) : Interceptor<Log<LOG>>() {
    /**
     * A list for counting event
     */
    private val list = mutableListOf<Log<LOG>>()
    private var lastFlushTime = 0L
    private val scope = CoroutineScope(SupervisorJob())
    private var flushJob: Job? = null

    override fun log(tag: String, log: Log<LOG>, priority: Int, chain: Chain, vararg args: Any) {
        if (isLoggable(log)) {
            list.add(log)
            flushJob?.cancel()
            if (isOkFlush()) {
                flush(chain, tag, priority)
            } else {
                flushJob = delayFlush(chain, tag, priority)
            }
        }
    }

    private fun isOkFlush() = lastFlushTime != 0L && SystemClock.elapsedRealtime() - lastFlushTime >= interval || list.size >= size

    private fun flush(chain: Chain, tag: String, priority: Int) {
        val logs = pipeline.pack(list.map { it.data })
        val logBatch = LogBatch(list.map { it.id }, logs)
        chain.proceed(tag, logBatch, priority)
        list.clear()
        lastFlushTime = SystemClock.elapsedRealtime()
    }

    private fun delayFlush(chain: Chain, tag: String, priority: Int) = scope.launch(singleLogDispatcher) {
        val delayTime = if (lastFlushTime == 0L) interval else interval - (SystemClock.elapsedRealtime() - lastFlushTime)
        delay(delayTime)
        flush(chain, tag, priority)
    }

}