package com.architecture.httplib.core

import com.architecture.httplib.error.BusinessException
import java.io.IOException
import okhttp3.Request
import okio.Timeout
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

/**
 *重新定义Call，转发到Htt__KEEP以及__11__esult错误转换Handler
 *
 * Call<T> 接口的作用：该接口主要的作用就是发送一个HTTP请求，Retrofit默认的实现是OkHttpCall<T>，你可以根据实际情况实现你自己的Call类
 * 这里定义HttpResultCall是为了
 *
 * https://github.com/AnyLifeZLB
 *
 * @参数S
 * @pr操作调用
 * @property错误转换器
 *@作者anylife。zlb@gmail.com
 */
// 重命名 NetworkResponseCall ---> HttpResponseCall
internal class HttpResponseCall<S : Any>(
    private val call: Call<S>,
    private val errorConverter: HttpResponseCallAdapterFactory.ErrorHandler?,
) : Call<HttpResult<S>> {

    /**
     * 异步发送请求并通知调用回调返回的响应体或者错误信息
     *
     *callback.onResponse(Call<T> 呼叫, Response<T> 响应);
     * 回调.onResponse(this@HttpResponseCall,Response.success(HttpResult.Success(body)))
     *
     *打回来。onResponse(this@HttpResponseCall,响应。success([yourCustomResponse])) 差异在
     * [yourCustomResponse] 这里都用Response。成功了
     *
     * @paramcallback Http请求的回调方法，其中<HttpResult<S>> 成功的响应体类型。*/
    override fun enqueue(callback: Callback<HttpResult<S>>) {
        return call.enqueue(
            object : Callback<S> {

                /**
                 * @参数调用
                 * @参数响应
                 */
                override fun onResponse(call: Call<S>, response: Response<S>) {
                    val data = response.body()
                    val code = response.code()
                    val error = response.errorBody()
// HTTP 返回[200..300).
                    if (response.isSuccessful) {

                        if (data != null) {
                            callback.onResponse(
                                this@HttpResponseCall,
                                Response.success(HttpResult.Success(data)),
                            )
                        } else {
// body 为 null，这也是一个异常错误。会有吗？
// 打回来。响应（
//这个@HttpResponseCall，
//
// Response.success(HttpResult.未知错误（空））
// )

                            callback.onResponse(
                                this@HttpResponseCall,
                                Response.success(
                                    HttpResult.Failure(
                                        "response body is null",
                                        HttpResult.ErrorCode.EmptyResponse.value,
                                    )
                                ),
                            )
                        }
                    } else {
// 这是[4xx, 5xx] 的错误信息，这也是Http返回比较具体的错误（如果是异常就是直接onFailed了）
// if (错误！= null && 错误。内容长度() > 0) {
// // 有明确的返回错误
//
// // 500X
// val 错误响应 =
// MoshiUtils。来自Json<BusinessBaseResponse>(
// 错误。细绳（），
// BusinessBaseResponse::类。爪哇
// )
//
// // ?????????压测一遍
// 错误转换器？失败（
// 业务异常(
// 错误响应？.code ?：-1，
// 错误响应？.消息？：“”
// )
// )
//
//// 打回来。响应（
////这个@HttpResponseCall，
//// 回复。成功（
//// HttpR结果。Api错误（
//// 错误响应？.消息？：“”，
//// 错误响应？.code ?：-1
//// )
//// )
//// )
//
// 打回来。响应（
//这个@HttpResponseCall，
// 回复。成功（
// HttpR结果。失败（
// 错误响应？.消息？：“”，
// 错误响应？.code ?：-1
// )
// )
// )
//
//
// }另外{
// 没有Error Body的情况
                        callback.onResponse(
                            this@HttpResponseCall,
                            Response.success(
                                HttpResult.Failure(error?.string() ?: "Message is empty.", code)
                            ),
                        )
// }
                    }
                }

                /**
                 * 失败，还有各种Exception
                 *
                 * [-1,-100] 业务方不要占用，作为谋求全局公共错误码
                 */
                override fun onFailure(call: Call<S>, throwable: Throwable) {
                    val networkResponse =
                        when (throwable) {
// 是 IOException -> HttpResult。网络错误（
//可发送的。消息。到字符串（），
// 400
// )
//
// 是 BusinessException -> {
// 错误转换器？onFailure（可提交）
// HttpResult.ApiError(throwable.message ?：“”，
// 可转发的。代码）
// }
// IO Exception 太宽泛了，需要具体一点
                            is IOException -> HttpResult.Failure(throwable.message.toString(), -1)
// 这是Moshi 解析代码！= OK-Code 的时候抛出的异常错误，业务服务器会给出详细的错误
// 强烈建议业务服务器给出的错误编码不要和传统的Http请求的代码有重合，负数最好
                            is BusinessException -> {
                                errorConverter?.onFailure(throwable) // ???
                                HttpResult.Failure(throwable.message ?: "", throwable.code)
                            }
// 尽力拓展完整一点
                            else -> {
                                HttpResult.Failure(throwable.message ?: "unknow error", -2)
                            }
                        }

                    callback.onResponse(this@HttpResponseCall, Response.success(networkResponse))
                }
            }
        )
    }

    /**
     * 暂时不支持吧，拦截处理Token跨境不是很有用吗？
     *
     * @返回
     */
    override fun execute(): Response<HttpResult<S>> {
        throw UnsupportedOperationException("HttpResponseCall doesn't support execute")
    }

    override fun isExecuted() = call.isExecuted

    override fun clone() = HttpResponseCall(call.clone(), errorConverter)

    override fun isCanceled() = call.isCanceled

    override fun cancel() = call.cancel()

    override fun request(): Request = call.request()

    override fun timeout(): Timeout = call.timeout()
}
