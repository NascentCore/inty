package com.inty.utils.log

import com.inty.utils.log.interceptor.BatchInterceptor
import com.inty.utils.log.interceptor.FileInterceptor
import com.inty.utils.log.interceptor.LinearInterceptor
import com.inty.utils.log.interceptor.LogInterceptor
import com.inty.utils.log.interceptor.LogcatInterceptor
import com.inty.utils.log.interceptor.SinkInterceptor
import com.inty.utils.log.interceptor.UploadInterceptor

/**
 * A build-in log chain.
 * All Logs will be stored in mmkv and uploaded in batch
 */
fun EasyLog.simpleInit(size: Int, duration: Long, pipeline: Pipeline<*, *>, isLoggable: (Any) -> Boolean = { true }) {
    EasyLog.apply {
        addInterceptor(LogcatInterceptor())
        addInterceptor(LinearInterceptor())
        addInterceptor(LogInterceptor(), isLoggable)
        addInterceptor(SinkInterceptor(pipeline))
        addInterceptor(BatchInterceptor(size, duration, pipeline))
        addInterceptor(UploadInterceptor(pipeline))
    }
}

fun EasyLog.defaultInit() {
    EasyLog.apply {
        addInterceptor(LogcatInterceptor())
//        addInterceptor(FileInterceptor())
    }
}