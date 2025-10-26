package com.architecture.httplib.core

import com.architecture.httplib.error.BusinessException
import java.lang.reflect.ParameterizedType
import java.lang.reflect.Type
import retrofit2.Call
import retrofit2.CallAdapter
import retrofit2.Retrofit

/**
 * 作用：将默认的网络请求执行器（OkHttpCall）转换成适合被不同平台调用的网络请求执行器形式
 *
 * 在Retrofit中提供了四种CallAdapterFactory：Executor（默认）、Guava 、Java8 、RxJava
 *
 * 扩展CallAdapter
 *
 * Call<T> --> HttpResponseCall<T> 就是为了返回HttpResult<T>
 *
 * 暂停 getFakerData(): HttpResult<List<FakerDataBean>>
 *
 * https://github.com/AnyLifeZLB
 *
 *@作者anylife。zlb@gmail.com
 */
class HttpResponseCallAdapterFactory(private val errorHandler: ErrorHandler? = null) :
    CallAdapter.Factory() {

    /** [onFailure] 将在 [Result.失败] */
    fun interface ErrorHandler {
        fun onFailure(throwable: BusinessException)
    }

    override fun get(
        returnType: Type,
        annotations: Array<Annotation>,
        retrofit: Retrofit,
    ): CallAdapter<*, *>? {
// 挂起函数将响应类型封装在 `Call` 中
        if (Call::class.java != getRawType(returnType)) {
            return null
        }
// 首先检查返回类型是否为 `ParameterizedType`
        check(returnType is ParameterizedType) {
            "return type must be parameterized as Call<HttpResult<<Foo>> or Call<HttpResult<out Foo>>"
        }
// 获取`Call`类型中的响应类型
        val responseType = getParameterUpperBound(0, returnType)
// 类型检查
// 如果响应类型不是 ApiResponse 现在我们无法处理这种类型，所以我们返回 null
        if (getRawType(responseType) != HttpResult::class.java) {
            return null
        }
// 响应类型是 ApiResponse 并且应该参数化
        check(responseType is ParameterizedType) {
            "Response must be parameterized as HttpResult<Foo> or HttpResponse<out Foo>"
        }
// 上面是一些基本的参数检查，类型匹配
// 这里第一主角，Call<Any> ---> HttpResponseCall
        return object : CallAdapter<Any, Call<*>?> {

            override fun responseType(): Type {
                return responseType
            }

            override fun adapt(call: Call<Any>): Call<*> {
// 暂停乐趣 getFakerData(): HttpResult<List<FakerDataBean>>
// 就是为了返回HttpResult<T>这个啊
                return HttpResponseCall(call, errorHandler)
            }
        }
    }
}
