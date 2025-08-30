package com.inty.utils.log.interceptor

import com.inty.utils.log.Chain
import com.inty.utils.log.Interceptor

class FrameInterceptor : Interceptor<Any>() {
    private val HEADER =
        "┌──────────────────────────────────────────────────────────────────────────────────────────────────────"
    private val FOOTER =
        "└──────────────────────────────────────────────────────────────────────────────────────────────────────"
    private val LEFT_BORDER = '│'

    override fun log(tag: String, message: Any, priority: Int, chain: Chain, vararg args: Any) {
        val msg = HEADER + "\n" + LEFT_BORDER + message + "\n" + FOOTER
        chain.proceed(tag,msg, priority, args)
    }

}