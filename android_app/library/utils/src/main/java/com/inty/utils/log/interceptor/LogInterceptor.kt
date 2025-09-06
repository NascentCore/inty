package com.inty.utils.log.interceptor

import com.inty.utils.log.Chain
import com.inty.utils.log.Interceptor
import com.inty.utils.log.model.Log
import java.util.UUID

class LogInterceptor : Interceptor<Any>() {
    override fun log(tag: String, message: Any, priority: Int, chain: Chain, vararg args: Any) {
        if (isLoggable(message)) chain.proceed(tag, Log(UUID.randomUUID().toString(), message), priority, args)
    }

}