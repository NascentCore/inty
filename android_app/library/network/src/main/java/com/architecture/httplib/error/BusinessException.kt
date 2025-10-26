package com.architecture.httplib.error

/** 业务的错误，错误码+ errorString */
class BusinessException(val code: Int, message: String?) : RuntimeException(message)
