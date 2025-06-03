package com.ai.inty.net

import com.ai.inty.Constant
import com.architecture.httplib.core.HttpResponseCallAdapterFactory
import com.architecture.httplib.core.MoshiResultTypeAdapterFactory
import com.architecture.httplib.error.GlobalErrorHandler
import com.chuckerteam.chucker.api.ChuckerInterceptor
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.jakewharton.retrofit2.adapter.kotlin.coroutines.CoroutineCallAdapterFactory
import com.squareup.moshi.DefaultIfNullFactory
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import com.therouter.inject.ServiceProvider
import com.therouter.inject.Singleton
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit


class AuthInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request =
            chain.request().newBuilder()
                .addHeader("accept", "application/json")
                .addHeader("Content-Type", "application/json")
                .build()

        return chain.proceed(request)
    }

}

object NetServiceMgr {

    val authInterceptor = AuthInterceptor()
    val okHttpClient: OkHttpClient
        get() {
            val builder: OkHttpClient.Builder = OkHttpClient.Builder()
                .connectTimeout(5, TimeUnit.SECONDS)
                .writeTimeout(5, TimeUnit.SECONDS)
                .readTimeout(50, TimeUnit.SECONDS)
                .addInterceptor(authInterceptor)
                .addInterceptor(ChuckerInterceptor(AppEnv.context))
            return builder.build()
        }
    val moshi: Moshi
        get() {
            return Moshi.Builder()
                //添加返回的json 数据自定义解析器
                .add(DefaultIfNullFactory())
                .add(MoshiResultTypeAdapterFactory(getHttpWrapperHandler()))
                .addLast(KotlinJsonAdapterFactory()) //
                .build()
        }

    private val globalErrorHandler = GlobalErrorHandler()

    private fun getHttpWrapperHandler(): MoshiResultTypeAdapterFactory.HttpWrapper{

        return object : MoshiResultTypeAdapterFactory.HttpWrapper {
            override fun getStatusCodeKey(): String {
                return "code"
            }

            override fun getErrorMsgKey(): String {
                return "message"
            }

            override fun getDataKey(): String {
                return "data"
            }

            override fun isRequestSuccess(statusCode: Int): Boolean {
                return statusCode == 200   //200 表示业务上是正确返回了数据
            }
        }
    }

    fun baseUrl(): String {
        if (AppEnv.testEnv) {
            return "https://${Constant.USER_HOST_DEV}/"
        } else {
            return "https://${Constant.USER_HOST}/"
        }
    }

    val retrofitNormal: Retrofit
        get() {

            val retrofitUser =
                Retrofit.Builder()
                    .baseUrl(baseUrl())
                    .client(okHttpClient)
                    .addConverterFactory(MoshiConverterFactory.create(moshi))
                    .addCallAdapterFactory(CoroutineCallAdapterFactory())
                    .addCallAdapterFactory(
                        HttpResponseCallAdapterFactory(globalErrorHandler) //全局的错误处理器
                    )
                    .build()

            return retrofitUser
        }

}

@ServiceProvider
fun getUserApi(): IUserApi {
    return NetServiceMgr.retrofitNormal.create(IUserApi::class.java)
}
