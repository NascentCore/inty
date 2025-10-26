package com.architecture.httplib.error

import com.architecture.httplib.core.HttpResponseCallAdapterFactory

/**
 * 全局的错误请求拦截处理，比如Token过渡实现之类的问题，要立马到跳转登录页面
 *
 * 根据业务场景完善升级
 */
class GlobalErrorHandler : HttpResponseCallAdapterFactory.ErrorHandler {
    override fun onFailure(throwable: BusinessException) {
        when (throwable.code) {
            101 -> {}

            102 -> {}
        }
    }
}
