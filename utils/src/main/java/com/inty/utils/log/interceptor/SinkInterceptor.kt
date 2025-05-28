package com.inty.utils.log.interceptor

import com.inty.utils.log.Chain
import com.inty.utils.log.Interceptor
import com.inty.utils.log.Pipeline
import com.inty.utils.log.model.Log
import com.tencent.mmkv.MMKV

class SinkInterceptor<LOG>(private val pipeline: Pipeline<LOG, *>) : Interceptor<Log<LOG>>() {
    companion object {
        val mmkv by lazy { MMKV.defaultMMKV() }
    }

    override fun log(tag: String, message: Log<LOG>, priority: Int, chain: Chain, vararg args: Any) {
        if (isLoggable(message)) mmkv.encode(message.id, pipeline.toByteArray(message.data))
        chain.proceed(tag, message, priority)
    }
}