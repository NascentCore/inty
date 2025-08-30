package com.inty.utils.log.interceptor

import com.inty.utils.log.Chain
import com.inty.utils.log.Interceptor
import com.inty.utils.log.Pipeline
import com.inty.utils.log.model.LogBatch
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class UploadInterceptor<LOG, LOGS>(private val pipeline: Pipeline<LOG, LOGS>) : Interceptor<LogBatch<LOGS>>() {
    private val scope by lazy { CoroutineScope(SupervisorJob() + Dispatchers.IO) }

    override fun log(tag: String, logs: LogBatch<LOGS>, priority: Int, chain: Chain, vararg args: Any) {
        if (isLoggable(logs)) scope.launch {
            val result = pipeline.upload(logs.data)
            if (result) SinkInterceptor.mmkv.removeValuesForKeys(logs.ids.toTypedArray())
        }
    }

}