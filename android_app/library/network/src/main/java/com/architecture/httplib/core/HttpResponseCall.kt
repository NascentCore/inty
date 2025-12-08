package com.architecture.httplib.core

import com.architecture.httplib.error.BusinessException
import java.io.IOException
import okhttp3.Request
import okio.Timeout
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

/**
 * 重新定义Call,适配到HttpResult 以及错误转换Handler
 *
 * Call<T> 接口的作用： 这个接口主要的作用就是发送一个HTTP请求，Retrofit默认的实现是OkHttpCall<T>，你可以根据实际情况实现你自己的Call类
 * 这里定义HttpResultCall是为了
 *
 * https://github.com/AnyLifeZLB
 *
 * @param S
 * @property call
 * @property errorConverter
 * @author anylife.zlb@gmail.com
 */
// Rename NetworkResponseCall ---> HttpResponseCall
internal class HttpResponseCall<S : Any>(
    private val call: Call<S>,
    private val errorConverter: HttpResponseCallAdapterFactory.ErrorHandler?,
) : Call<HttpResult<S>> {

    /**
     * 异步发送请求并通知调用回调返回的 response body或者 错误信息
     *
     * callback.onResponse(Call<T> call, Response<T> response);
     * callback.onResponse(this@HttpResponseCall,Response.success(HttpResult.Success(body)))
     *
     * callback.onResponse(this@HttpResponseCall,Response.success([yourCustomResponse])) 差异在
     * [yourCustomResponse] 这里都用Response.success 了
     *
     * @param callback Http 请求的回调方法 ，其中<HttpResult<S>> Successful response body type.
     */
    override fun enqueue(callback: Callback<HttpResult<S>>) {
        return call.enqueue(
            object : Callback<S> {

                /**
                 * @param call
                 * @param response
                 */
                override fun onResponse(call: Call<S>, response: Response<S>) {
                    val data = response.body()
                    val code = response.code()
                    val error = response.errorBody()

                    // Http 返回[200..300).
                    if (response.isSuccessful) {

                        if (data != null) {
                            callback.onResponse(
                                this@HttpResponseCall,
                                Response.success(HttpResult.Success(data)),
                            )
                        } else {
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
                        callback.onResponse(
                            this@HttpResponseCall,
                            Response.success(
                                HttpResult.Failure(error?.string() ?: "Message is empty.", code)
                            ),
                        )
                    }
                }

                /**
                 * 失败，还有各种Exception
                 *
                 * [-1,-100] 业务方不要占用了，作为预留全局公共错误码
                 */
                override fun onFailure(call: Call<S>, throwable: Throwable) {
                    val networkResponse =
                        when (throwable) {
                            // IO Exception 太宽泛了，需要具体一点
                            is IOException -> HttpResult.Failure(throwable.message.toString(), -1)

                            // 这个是Moshi 解析 code ！= OK-Code 的时候抛出的异常错误，业务服务器会给出详细的错误
                            // 强烈建议业务服务器给的错误编码不要和传统的Http 请求的Code 有重合，负数最好
                            is BusinessException -> {
                                errorConverter?.onFailure(throwable) // ???
                                HttpResult.Failure(throwable.message ?: "", throwable.code)
                            }

                            // 尽量拓展完整一点
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
     * 暂时不支持吧，拦截处理Token 过期不是很有用吗？
     *
     * @return
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
