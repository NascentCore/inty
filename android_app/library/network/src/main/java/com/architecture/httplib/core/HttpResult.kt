package com.architecture.httplib.core

/**
 * 定义密封类，就是一个枚举
 *
 * HTTP 返回常见的状态码 200 OK //客户端请求成功 400 Bad Request //客户端请求有语法错误，不能被服务器所理解 401 Unauthorized
 * // 请求未授权，该状态代码必须和WWW-Authenticate报头域一起使用 403 Forbidden // 服务器接收请求，但拒绝提供服务 404 Not Found
 * //请求资源不存在，eg：输入了错误的URL 500 Internal Server Error //服务器发生不可预期的错误 503 Server Unavailable
 * // 服务端当前无法处理客户端的请求，一段时间后可能会恢复正常
 *
 *注意Http的状态码和我们业务定义的代码不是一回事，业务定义的代码完全是自由定义的，不要混淆了
 *
 * https://github.com/AnyLifeZLB
 *
 *@作者anylife。zlb@gmail。com*/
sealed class HttpResult<out T : Any> {

    enum class ErrorCode(val value: Int) {
        EmptyResponse(-111)
    }
// 200-300就是成功，body就是业务上真实的成功的时候需要的数据
    data class Success<T : Any>(val data: T) : HttpResult<T>()
// 各种失败，异常全部到这里来吧
    data class Failure(val message: String, val code: Int) : HttpResult<Nothing>()
}
