package com.ai.inty.net

import android.content.Context
import android.content.Intent
import com.ai.inty.Constant
import com.architecture.httplib.core.HttpResponseCallAdapterFactory
import com.architecture.httplib.core.MoshiResultTypeAdapterFactory
import com.architecture.httplib.error.GlobalErrorHandler
import com.chuckerteam.chucker.api.ChuckerInterceptor
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.jakewharton.retrofit2.adapter.kotlin.coroutines.CoroutineCallAdapterFactory
import com.squareup.moshi.DefaultIfNullFactory
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import com.therouter.inject.ServiceProvider
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
//                .addHeader("Content-Type", "application/json")
                .addHeader("Authorization", "Bearer ${IntySetting.getCurToken()}")
                .build()

        EasyLog.log("request = $request")
        val response = chain.proceed(request)

        when (response.code) {
            401 -> {
                EasyLog.log("http 401 for ${request.url}", EasyLog.ERROR)
                // 检查是否正在退出登录过程中，避免重复重启
                if (IntySetting.isLoggingOut()) {
                    EasyLog.log("Ignoring 401 during logout process")
                } else {
                    EasyLog.log("401 unauthorized - switching to guest mode")
                    IntySetting.logout()
                    restartAppProcess(context = AppEnv.context)
                }
            }
        }

        return response
    }

}


private fun restartAppProcess(context: Context) {
    val intent = context.packageManager.getLaunchIntentForPackage(context.packageName)
    intent?.apply {
        addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP) // 清除历史栈
        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)  // 新任务栈
        context.startActivity(this)
    }
    // 终止当前进程
    android.os.Process.killProcess(android.os.Process.myPid())
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
    val moshiNoWrapper: Moshi
        get() {
            return Moshi.Builder()
                //添加返回的json 数据自定义解析器
                .add(DefaultIfNullFactory())
                .add(MoshiResultTypeAdapterFactory(null))
                .addLast(KotlinJsonAdapterFactory()) //
                .build()
        }

    private val globalErrorHandler = GlobalErrorHandler()

    private fun getHttpWrapperHandler(): MoshiResultTypeAdapterFactory.HttpWrapper {

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
        return if (AppEnv.testEnv) {
            "https://${Constant.USER_HOST_DEV}/"
        } else {
            "https://${Constant.USER_HOST}/"
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

    val retrofitNoWrapper: Retrofit
        get() {

            val retrofitUser =
                Retrofit.Builder()
                    .baseUrl(baseUrl())
                    .client(okHttpClient)
                    .addConverterFactory(MoshiConverterFactory.create(moshiNoWrapper))
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

@ServiceProvider
fun getUserApi2(): IUserApi2 {
    return NetServiceMgr.retrofitNoWrapper.create(IUserApi2::class.java)
}

@ServiceProvider
fun getAgentApi(): IAgentApi {
    return NetServiceMgr.retrofitNormal.create(IAgentApi::class.java)
}

@ServiceProvider
fun getChatApi(): IChatApi {
    return NetServiceMgr.retrofitNoWrapper.create(IChatApi::class.java)
}

@ServiceProvider
fun getReportApi(): IReportApi {
    return NetServiceMgr.retrofitNormal.create(IReportApi::class.java)
}

@ServiceProvider
fun getSubscriptionApi(): ISubscriptionApi {
    return NetServiceMgr.retrofitNormal.create(ISubscriptionApi::class.java)
}