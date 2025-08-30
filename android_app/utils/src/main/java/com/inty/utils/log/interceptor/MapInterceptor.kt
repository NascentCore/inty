package com.inty.utils.log.interceptor

import com.inty.utils.log.Chain
import com.inty.utils.log.Interceptor
import com.inty.utils.log.log

/**
 * An [Interceptor] for print [Map]
 */
class MapInterceptor<K, V> : Interceptor<Map<K, V>>() {
    override fun log(tag: String, message: Map<K, V>, priority: Int, chain: Chain, vararg args: Any) {
        if (isLoggable(message)) chain.proceed(tag, message.log(4), priority, args)
        else chain.proceed(tag, message, priority, args)
    }

}